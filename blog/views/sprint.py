from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import ListView, UpdateView

from ..forms import SprintAdminForm, SprintStatusForm
from ..models import Project, Sprint
from .permissions import can_manage_sprints, is_admin, visible_projects
from .queries import capacity_rows, project_backlog_queryset, save_sprint_user_capacities


class SprintAdminIndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Project
    template_name = "blog/sprint_admin_index.html"
    context_object_name = "projects"

    def test_func(self):
        return is_admin(self.request.user)

    def get_queryset(self):
        return visible_projects(self.request.user).order_by("name")


class SprintUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Sprint
    form_class = SprintAdminForm
    template_name = "blog/sprint_form.html"

    def test_func(self):
        sprint = self.get_object()
        return can_manage_sprints(self.request.user, sprint.project)

    def get_success_url(self):
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url:
            return next_url
        return reverse("sprint-admin", kwargs={"pk": self.object.project.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["capacity_rows"] = capacity_rows(
            self.object.project,
            post_data=self.request.POST if self.request.method == "POST" else None,
            sprint=self.object,
        )
        return ctx

    def form_valid(self, form):
        self.object = form.save(commit=False)
        try:
            with transaction.atomic():
                self.object.save()
                save_sprint_user_capacities(self.object, self.request.POST)
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
            return self.form_invalid(form)
        messages.success(self.request, "Sprint updated successfully.")
        return redirect(self.get_success_url())


@login_required
def sprint_admin(request, pk):
    project = get_object_or_404(visible_projects(request.user), pk=pk)

    if not can_manage_sprints(request.user, project):
        messages.error(request, "Access denied.")
        return redirect("blog-home")

    if request.method == "POST":
        return _handle_sprint_creation(request, project)

    context = {
        "project": project,
        "form": SprintAdminForm(),
        "capacity_rows": capacity_rows(project),
        "sprints": [(sprint, SprintStatusForm(sprint=sprint)) for sprint in project.sprints.all()],
        "title": "Administration des sprints",
    }
    return render(request, "blog/sprint_admin.html", context)


def _handle_sprint_creation(request, project):
    form = SprintAdminForm(request.POST)
    rows = capacity_rows(project, post_data=request.POST)

    if form.is_valid():
        sprint = form.save(commit=False)
        sprint.project = project
        sprint.created_by = request.user
        try:
            with transaction.atomic():
                sprint.save()
                save_sprint_user_capacities(sprint, request.POST)
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            messages.success(request, f"Le sprint '{sprint.name}' a été créé.")
            return redirect("sprint-admin", pk=project.pk)

    context = {
        "project": project,
        "form": form,
        "capacity_rows": rows,
        "sprints": [(sprint, SprintStatusForm(sprint=sprint)) for sprint in project.sprints.all()],
        "title": "Administration des sprints",
    }
    return render(request, "blog/sprint_admin.html", context)


@login_required
def sprint_start(request, pk):
    sprint = get_object_or_404(Sprint.objects.select_related("project"), pk=pk)
    if not can_manage_sprints(request.user, sprint.project):
        messages.error(request, "Access denied.")
        return redirect("blog-home")
    if request.method != "POST":
        return redirect("project-backlog", pk=sprint.project_id)
    try:
        sprint.start()
        messages.success(request, f"Le sprint '{sprint.name}' est maintenant actif.")
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect("project-backlog", pk=sprint.project_id)


@login_required
def sprint_close(request, pk):
    sprint = get_object_or_404(Sprint.objects.select_related("project"), pk=pk)
    if not can_manage_sprints(request.user, sprint.project):
        messages.error(request, "Access denied.")
        return redirect("blog-home")
    if request.method != "POST":
        return redirect("project-backlog", pk=sprint.project_id)
    try:
        sprint.close()
        messages.success(request, f"Le sprint '{sprint.name}' a été clôturé.")
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect("project-backlog", pk=sprint.project_id)


@login_required
def update_sprint_status(request, pk):
    sprint = get_object_or_404(Sprint.objects.select_related("project"), pk=pk)
    if not can_manage_sprints(request.user, sprint.project):
        messages.error(request, "Access denied.")
        return redirect("blog-home")
    if request.method != "POST":
        return redirect("sprint-admin", pk=sprint.project_id)

    form = SprintStatusForm(request.POST, sprint=sprint)
    if not form.is_valid():
        messages.error(request, "Le statut demandé est invalide.")
        return redirect("sprint-admin", pk=sprint.project_id)

    new_status = form.cleaned_data["status"]
    try:
        _apply_sprint_status_transition(sprint, new_status, request)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])

    return redirect("sprint-admin", pk=sprint.project_id)


def _apply_sprint_status_transition(sprint, new_status, request):
    if new_status == sprint.status:
        messages.success(
            request,
            f"Le sprint '{sprint.name}' est déjà en statut {sprint.get_status_display().lower()}.",
        )
    elif sprint.status == Sprint.STATUS_PLANNED and new_status == Sprint.STATUS_ACTIVE:
        sprint.start()
        messages.success(request, f"Le sprint '{sprint.name}' est maintenant actif.")
    elif sprint.status == Sprint.STATUS_ACTIVE and new_status == Sprint.STATUS_CLOSED:
        sprint.close()
        messages.success(request, f"Le sprint '{sprint.name}' a été clôturé.")
    else:
        messages.error(request, "Cette transition de statut n'est pas prise en charge depuis cette page.")


@login_required
def delete_sprint(request, pk):
    sprint = get_object_or_404(Sprint.objects.select_related("project"), pk=pk)
    if not can_manage_sprints(request.user, sprint.project):
        messages.error(request, "Access denied.")
        return redirect("blog-home")

    if request.method == "POST":
        if sprint.status == Sprint.STATUS_ACTIVE:
            messages.error(request, "An active sprint cannot be deleted.")
            return redirect("sprint-admin", pk=sprint.project.pk)
        sprint.delete()
        messages.success(request, "Sprint deleted successfully.")
        return redirect("sprint-admin", pk=sprint.project.pk)

    return render(request, "blog/sprint_confirm_delete.html", {"sprint": sprint})


@login_required
def move_backlog_ticket(request, pk, direction):
    from ..models import Ticket
    ticket = get_object_or_404(
        Ticket.objects.select_related("project", "sprint"),
        pk=pk,
        issue_type__in=[Ticket.ISSUE_TYPE_STORY, Ticket.ISSUE_TYPE_BUG],
    )
    if not can_manage_sprints(request.user, ticket.project):
        messages.error(request, "Access denied.")
        return redirect("blog-home")

    backlog_items = list(project_backlog_queryset(ticket.project))
    ids = [item.pk for item in backlog_items]

    if ticket.pk not in ids:
        messages.error(request, "Ce ticket n'est pas réordonnable dans le Product Backlog.")
        return redirect("project-backlog", pk=ticket.project_id)

    current_index = ids.index(ticket.pk)
    other = _find_swap_target(backlog_items, current_index, direction)

    if other is None:
        return redirect("project-backlog", pk=ticket.project_id)

    with transaction.atomic():
        ticket.backlog_order, other.backlog_order = other.backlog_order, ticket.backlog_order
        ticket.save(update_fields=["backlog_order"])
        other.save(update_fields=["backlog_order"])

    messages.success(request, "La priorité relative du backlog a été mise à jour.")
    return redirect("project-backlog", pk=ticket.project_id)


def _find_swap_target(backlog_items, current_index, direction):
    if direction == "up" and current_index > 0:
        return backlog_items[current_index - 1]
    if direction == "down" and current_index < len(backlog_items) - 1:
        return backlog_items[current_index + 1]
    return None


