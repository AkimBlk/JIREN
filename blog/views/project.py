from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import ProjectForm
from ..models import Project, ProjectMember, Sprint, Tag, Ticket
from .permissions import can_contribute, can_create_projects, can_manage_sprints, is_admin, visible_projects
from .queries import filter_tickets_by_tag, project_backlog_queryset, resolve_tag_filter


class ProjectHomeView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "blog/home_projects.html"
    context_object_name = "projects"

    def get_queryset(self):
        return visible_projects(self.request.user).order_by("-date_created")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user_is_admin"] = is_admin(self.request.user)
        ctx["user_can_create_projects"] = can_create_projects(self.request.user)
        return ctx


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "blog/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return visible_projects(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["members"] = (
            ProjectMember.objects.filter(project=self.object)
            .select_related("user")
            .order_by("user__username")
        )
        project_tickets = self.object.tickets.all()
        available_tags, selected_tag = resolve_tag_filter(self.request, project_tickets)
        ctx["project_tickets"] = (
            filter_tickets_by_tag(project_tickets, selected_tag)
            .select_related("epic", "sprint", "assignee")
            .prefetch_related("tags")
            .order_by("backlog_order", "id")
        )
        ctx["available_tags"] = available_tags
        ctx["selected_tag"] = selected_tag
        ctx["user_is_admin"] = is_admin(self.request.user)
        ctx["user_can_create_ticket"] = can_contribute(self.request.user)
        ctx["user_can_manage_sprints"] = can_manage_sprints(self.request.user, self.object)
        ctx["active_sprint"] = (
            self.object.sprints.filter(status=Sprint.STATUS_ACTIVE).order_by("start_date", "id").first()
        )
        return ctx


class ProjectCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "blog/project_form.html"

    def test_func(self):
        return can_create_projects(self.request.user)

    def form_valid(self, form):
        form.instance.manager = self.request.user
        response = super().form_valid(form)
        form.sync_members(self.object, self.request.user)
        return response


class ProjectUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "blog/project_form.html"

    def test_func(self):
        project = self.get_object()
        return self.request.user == project.manager or is_admin(self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        form.sync_members(self.object, self.object.manager)
        return response


class ProjectDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Project
    template_name = "blog/project_confirm_delete.html"

    def get_success_url(self):
        return reverse("blog-home")

    def test_func(self):
        project = self.get_object()
        return self.request.user == project.manager or is_admin(self.request.user)


class ProjectBacklogView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "blog/project_backlog.html"
    context_object_name = "project"

    def get_queryset(self):
        return visible_projects(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object

        project_tickets = project.tickets.all()
        available_tags, selected_tag = resolve_tag_filter(self.request, project_tickets)

        epics = (
            filter_tickets_by_tag(
                Ticket.objects.filter(project=project, issue_type=Ticket.ISSUE_TYPE_EPIC),
                selected_tag,
            )
            .prefetch_related("tags")
            .order_by("title")
        )
        ctx["epics"] = epics
        ctx["backlog_items"] = list(filter_tickets_by_tag(project_backlog_queryset(project), selected_tag))
        ctx["available_tags"] = available_tags
        ctx["selected_tag"] = selected_tag
        ctx["sprint_blocks"] = self._build_sprint_blocks(project, selected_tag)
        ctx["user_is_admin"] = is_admin(self.request.user)
        return ctx

    def _build_sprint_blocks(self, project, selected_tag):
        return [
            (
                sprint,
                filter_tickets_by_tag(Ticket.objects.filter(sprint=sprint), selected_tag)
                .select_related("epic", "assignee")
                .prefetch_related("tags")
                .annotate(
                    priority_order=Case(
                        When(priority="HIGH", then=Value(1)),
                        When(priority="MEDIUM", then=Value(2)),
                        When(priority="LOW", then=Value(3)),
                        default=Value(99),
                        output_field=IntegerField(),
                    )
                )
                .order_by("priority_order", "backlog_order", "-date_posted", "id"),
            )
            for sprint in project.sprints.all()
        ]


@login_required
def project_active_sprint(request, pk):
    project = get_object_or_404(visible_projects(request.user), pk=pk)
    active_sprint = (
        project.sprints.filter(status=Sprint.STATUS_ACTIVE).order_by("start_date", "id").first()
    )
    if not active_sprint:
        messages.info(request, "Aucun sprint actif pour ce projet.")
        return redirect("project-detail", pk=project.pk)
    return redirect(f"{reverse('kanban')}?project={project.pk}")


@login_required
def delete_projects(request):
    if not is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("blog-home")
    if request.method != "POST":
        return redirect("blog-home")
    selected_ids = request.POST.getlist("project_ids")
    if not selected_ids:
        messages.warning(request, "No project selected.")
        return redirect("blog-home")
    Project.objects.filter(pk__in=selected_ids).delete()
    messages.success(request, "Selected projects deleted.")
    return redirect("blog-home")


