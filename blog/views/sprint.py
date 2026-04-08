import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
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
        "title": "Sprint Administration",
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
            messages.success(request, f"Sprint '{sprint.name}' created.")
            return redirect("sprint-admin", pk=project.pk)

    context = {
        "project": project,
        "form": form,
        "capacity_rows": rows,
        "sprints": [(sprint, SprintStatusForm(sprint=sprint)) for sprint in project.sprints.all()],
        "title": "Sprint Administration",
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
        messages.success(request, f"Sprint '{sprint.name}' is now active.")
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
        messages.success(request, f"Sprint '{sprint.name}' closed.")
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
        messages.error(request, "Requested status is invalid.")
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
            f"Sprint '{sprint.name}' is already {sprint.get_status_display().lower()}.",
        )
    elif sprint.status == Sprint.STATUS_PLANNED and new_status == Sprint.STATUS_ACTIVE:
        sprint.start()
        messages.success(request, f"Sprint '{sprint.name}' is now active.")
    elif sprint.status == Sprint.STATUS_ACTIVE and new_status == Sprint.STATUS_CLOSED:
        sprint.close()
        messages.success(request, f"Sprint '{sprint.name}' closed.")
    else:
        messages.error(request, "This status transition is not supported from this page.")


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
        issue_type__in=[
            Ticket.ISSUE_TYPE_STORY,
            Ticket.ISSUE_TYPE_BUG,
            Ticket.ISSUE_TYPE_TASK,
        ],
    )
    if not can_manage_sprints(request.user, ticket.project):
        messages.error(request, "Access denied.")
        return redirect("blog-home")

    if ticket.sprint_id:
        ordered_items = list(
            Ticket.objects.filter(sprint=ticket.sprint)
            .select_related("project", "sprint")
            .order_by("backlog_order", "date_posted", "id")
        )
        failure_message = "This ticket cannot be reordered in the sprint."
        success_message = "Sprint ticket order updated."
    else:
        ordered_items = list(project_backlog_queryset(ticket.project))
        failure_message = "This ticket cannot be reordered in the product backlog."
        success_message = "Backlog priority updated."

    ids = [item.pk for item in ordered_items]
    if ticket.pk not in ids:
        messages.error(request, failure_message)
        return redirect("project-backlog", pk=ticket.project_id)

    with transaction.atomic():
        needs_normalization = len(set(item.backlog_order for item in ordered_items)) < len(ordered_items)
        if needs_normalization:
            for i, item in enumerate(ordered_items):
                if item.backlog_order != i:
                    item.backlog_order = i
                    item.save(update_fields=["backlog_order"])
            ticket.refresh_from_db(fields=["backlog_order"])
            if ticket.sprint_id:
                ordered_items = list(
                    Ticket.objects.filter(sprint=ticket.sprint)
                    .select_related("project", "sprint")
                    .order_by("backlog_order", "date_posted", "id")
                )
            else:
                ordered_items = list(project_backlog_queryset(ticket.project))
            ids = [item.pk for item in ordered_items]

        current_index = ids.index(ticket.pk)
        other = _find_swap_target(ordered_items, current_index, direction)
        if other is None:
            return redirect("project-backlog", pk=ticket.project_id)

        ticket_obj = next(item for item in ordered_items if item.pk == ticket.pk)
        ticket_obj.backlog_order, other.backlog_order = other.backlog_order, ticket_obj.backlog_order
        ticket_obj.save(update_fields=["backlog_order"])
        other.save(update_fields=["backlog_order"])

    messages.success(request, success_message)
    return redirect("project-backlog", pk=ticket.project_id)


def _find_swap_target(backlog_items, current_index, direction):
    if direction == "up" and current_index > 0:
        return backlog_items[current_index - 1]
    if direction == "down" and current_index < len(backlog_items) - 1:
        return backlog_items[current_index + 1]
    return None


@login_required
@require_POST
def reorder_backlog(request, project_pk):
    from ..models import Ticket

    project = get_object_or_404(visible_projects(request.user), pk=project_pk)
    if not can_manage_sprints(request.user, project):
        return JsonResponse({"error": "Access denied."}, status=403)

    try:
        ordered_ids = json.loads(request.body).get("order", [])
        ordered_ids = [int(pk) for pk in ordered_ids]
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid payload."}, status=400)

    backlog_pks = set(project_backlog_queryset(project).values_list("pk", flat=True))
    if not all(pk in backlog_pks for pk in ordered_ids):
        return JsonResponse({"error": "Invalid ticket IDs."}, status=400)

    with transaction.atomic():
        for position, pk in enumerate(ordered_ids):
            Ticket.objects.filter(pk=pk).update(backlog_order=position)

    return JsonResponse({"ok": True})


@login_required
@require_POST
def reorder_sprint_tickets(request, sprint_pk):
    from ..models import Sprint, Ticket

    sprint = get_object_or_404(Sprint, pk=sprint_pk)
    if not can_manage_sprints(request.user, sprint.project):
        return JsonResponse({"error": "Access denied."}, status=403)

    try:
        ordered_ids = [int(pk) for pk in json.loads(request.body).get("order", [])]
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid payload."}, status=400)

    sprint_pks = set(Ticket.objects.filter(sprint=sprint).values_list("pk", flat=True))
    if not all(pk in sprint_pks for pk in ordered_ids):
        return JsonResponse({"error": "Invalid ticket IDs."}, status=400)

    with transaction.atomic():
        for position, pk in enumerate(ordered_ids):
            Ticket.objects.filter(pk=pk).update(backlog_order=position)

    return JsonResponse({"ok": True})
