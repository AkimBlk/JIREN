from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import ProjectForm
from ..models import Project, ProjectMember, Sprint, Tag, Ticket
from ..services import GitService
from .permissions import (
    can_contribute,
    can_create_projects,
    can_manage_sprints,
    get_project_role,
    is_admin,
    is_project_member,
    require_project_admin,
    visible_projects,
)
from .queries import filter_tickets_by_tag, project_backlog_queryset, resolve_tag_filter

PERCENTAGE_MULTIPLIER = 100
DECIMAL_PRECISION = 2


class ProjectHomeView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "blog/home_projects.html"
    context_object_name = "projects"

    def get_queryset(self):
        return (
            visible_projects(self.request.user)
            .select_related("manager")
            .prefetch_related("members__user")
            .annotate(
                ticket_count=Count("tickets", distinct=True),
                active_sprint_count=Count(
                    "sprints",
                    filter=Q(sprints__status=Sprint.STATUS_ACTIVE),
                    distinct=True,
                ),
            )
            .order_by("-date_created")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        projects = list(ctx["projects"])
        active_projects = 0
        total_members = 0
        total_tickets = 0

        for project in projects:
            members = sorted(project.members.all(), key=lambda membership: membership.user.username)
            project.member_count = len(members)
            preview_members = members[:4]
            project.preview_members = preview_members
            project.remaining_member_count = max(project.member_count - len(preview_members), 0)
            total_members += project.member_count
            total_tickets += project.ticket_count

            if project.active_sprint_count:
                project.dashboard_status = "Active"
                project.dashboard_status_class = "active"
                active_projects += 1
            elif project.start_date and project.start_date > today:
                project.dashboard_status = "Planned"
                project.dashboard_status_class = "planned"
            elif project.end_date and project.end_date < today:
                project.dashboard_status = "Completed"
                project.dashboard_status_class = "completed"
            else:
                project.dashboard_status = "On Track"
                project.dashboard_status_class = "track"

        ctx["projects"] = projects
        ctx["dashboard_summary"] = {
            "project_count": len(projects),
            "active_count": active_projects,
            "member_count": total_members,
            "ticket_count": total_tickets,
        }
        ctx["user_is_admin"] = is_admin(self.request.user)
        ctx["user_can_create_projects"] = can_create_projects(self.request.user)
        return ctx


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "blog/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return visible_projects(self.request.user).select_related("git_repository")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        members = (
            ProjectMember.objects.filter(project=self.object)
            .select_related("user")
            .order_by("user__username")
        )
        ctx["members"] = members
        project_tickets = self.object.tickets.all()
        available_tags, selected_tag = resolve_tag_filter(self.request, project_tickets)
        ctx["project_tickets"] = (
            filter_tickets_by_tag(project_tickets, selected_tag)
            .select_related("epic", "sprint", "assignee")
            .prefetch_related("tags")
            .order_by("backlog_order", "id")
        )
        ctx["commit_link_tickets"] = project_tickets.only("id", "title").order_by("backlog_order", "id")
        ctx["available_tags"] = available_tags
        ctx["selected_tag"] = selected_tag
        project_role = get_project_role(self.request.user, self.object)
        ctx["project_role"] = project_role
        ctx["user_is_admin"] = is_admin(self.request.user)
        ctx["user_can_create_ticket"] = can_contribute(self.request.user, self.object)
        ctx["user_can_manage_sprints"] = can_manage_sprints(self.request.user, self.object)
        ctx["active_sprint"] = (
            self.object.sprints.filter(status=Sprint.STATUS_ACTIVE).order_by("start_date", "id").first()
        )
        ctx["project_summary"] = {
            "ticket_count": project_tickets.count(),
            "in_progress_count": project_tickets.filter(status=Ticket.STATUS_IN_PROGRESS).count(),
            "done_count": project_tickets.filter(status=Ticket.STATUS_DONE).count(),
            "bug_count": project_tickets.filter(issue_type=Ticket.ISSUE_TYPE_BUG).count(),
            "member_count": members.count(),
        }
        ctx["recent_project_tickets"] = (
            project_tickets.select_related("epic", "assignee", "sprint")
            .prefetch_related("tags")
            .order_by("-date_posted", "-id")[:4]
        )

        # Add Git repository information if user has project access
        git_repository = getattr(self.object, "git_repository", None)
        ctx["git_repository"] = git_repository
        ctx["user_can_configure_git"] = is_project_member(self.request.user, self.object)
        ctx["git_info"] = self._get_git_info()
        ctx["git_commits"] = self._get_git_commits()
        ctx["git_branches"] = self._get_git_branches()
        ctx["git_extended_data"] = self._get_git_extended_metadata()

        # Add analytics chart data
        chart_data = self._calculate_chart_data()
        ctx.update(chart_data)

        return ctx

    def _get_git_info(self) -> dict:
        """Fetch Git repository info if user has project access."""
        if not self._user_has_project_access():
            return {}

        try:
            git_repo = self.object.git_repository
            git_service = GitService(git_repo)
            return git_service.get_repository_info()
        except Exception:
            return {}

    def _get_git_commits(self) -> list:
        """Fetch recent commits if user has project access."""
        if not self._user_has_project_access():
            return []

        try:
            git_repo = self.object.git_repository
            git_service = GitService(git_repo)
            return git_service.get_recent_commits()
        except Exception:
            return []

    def _get_git_branches(self) -> list:
        """Fetch branches if user has project access."""
        if not self._user_has_project_access():
            return []

        try:
            git_repo = self.object.git_repository
            git_service = GitService(git_repo)
            return git_service.get_branches()
        except Exception:
            return []

    def _get_git_extended_metadata(self) -> dict:
        """Fetch provider-specific extended metadata."""
        if not self._user_has_project_access():
            return {}

        try:
            git_repo = self.object.git_repository
            git_service = GitService(git_repo)
            return git_service.get_extended_metadata()
        except Exception:
            return {"error": "Failed to load Git metadata"}

    def _user_has_project_access(self) -> bool:
        """Check if current user is project member or owner."""
        if not hasattr(self.object, "git_repository"):
            return False
        return is_project_member(self.request.user, self.object)

    def _calculate_chart_data(self) -> dict:
        """Calculate analytics chart data for project."""
        closed_sprints = list(
            self.object.sprints.filter(status=Sprint.STATUS_CLOSED)
            .prefetch_related("tickets")
            .order_by("start_date")
        )

        # Check if project has any done tickets
        has_done_tickets = self.object.tickets.filter(status=Ticket.STATUS_DONE).exists()

        velocity_labels = []
        velocity_values = []
        consumption_values = []

        for sprint in closed_sprints:
            done_points = self._calculate_done_story_points(sprint)
            capacity = sprint.configured_capacity()

            consumption = 0
            if capacity > 0:
                consumption = round(
                    (done_points / capacity) * PERCENTAGE_MULTIPLIER,
                    DECIMAL_PRECISION,
                )

            velocity_labels.append(sprint.name)
            velocity_values.append(done_points)
            consumption_values.append(consumption)

        selected_sprint = closed_sprints[-1] if closed_sprints else None
        burndown = self._burndown_data(selected_sprint) if selected_sprint else None

        return {
            "has_done_tickets": has_done_tickets,
            "velocity_labels": velocity_labels,
            "velocity_values": velocity_values,
            "consumption_values": consumption_values,
            "burndown": burndown,
            "selected_sprint": selected_sprint,
        }

    def _calculate_done_story_points(self, sprint) -> int:
        """Calculate total story points marked as done in a sprint."""
        return (
            sprint.tickets.filter(status=Ticket.STATUS_DONE)
            .aggregate(total=Sum("story_points"))["total"]
            or 0
        )

    def _burndown_data(self, sprint) -> dict:
        """Generate burndown chart data for a sprint."""
        if not sprint:
            return None

        tickets = list(sprint.tickets.all())
        total_points = sum(t.story_points or 0 for t in tickets)

        if not total_points:
            return None

        days = []
        current_day = sprint.start_date
        while current_day <= sprint.end_date:
            days.append(current_day)
            current_day += timedelta(days=1)

        day_count = len(days)
        if day_count < 2:
            return None

        ideal_step = total_points / (day_count - 1)

        ideal = []
        actual = []
        done_so_far = sum(
            t.story_points or 0
            for t in tickets
            if t.status == Ticket.STATUS_DONE
        )
        remaining = max(total_points - done_so_far, 0)

        burn_step = (total_points - remaining) / (day_count - 1) if day_count > 1 else 0
        for i in range(day_count):
            ideal.append(round(total_points - (ideal_step * i), DECIMAL_PRECISION))
            actual.append(round(total_points - (burn_step * i), DECIMAL_PRECISION))

        return {
            "labels": [d.strftime("%d/%m") for d in days],
            "ideal": ideal,
            "actual": actual,
        }


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


class ProjectAdminRequiredMixin(LoginRequiredMixin):
    _project = None

    def get_object(self, queryset=None):
        if self._project is None:
            self._project = get_object_or_404(visible_projects(self.request.user), pk=self.kwargs["pk"])
        return self._project

    def dispatch(self, request, *args, **kwargs):
        require_project_admin(request.user, self.get_object())
        return super().dispatch(request, *args, **kwargs)


class ProjectUpdateView(ProjectAdminRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "blog/project_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        form.sync_members(self.object, self.object.manager)
        return response


class ProjectDeleteView(ProjectAdminRequiredMixin, DeleteView):
    model = Project
    template_name = "blog/project_confirm_delete.html"

    def get_success_url(self):
        return reverse("blog-home")


class ProjectBacklogView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "blog/project_backlog.html"
    context_object_name = "project"

    def get_queryset(self):
        return visible_projects(self.request.user).select_related("git_repository")

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
            .annotate(story_count=Count("stories", distinct=True))
            .prefetch_related("tags")
            .order_by("title")
        )
        backlog_items = list(filter_tickets_by_tag(project_backlog_queryset(project), selected_tag))
        active_sprint = (
            project.sprints.filter(status=Sprint.STATUS_ACTIVE)
            .order_by("start_date", "id")
            .first()
        )
        active_sprint_tickets = []
        active_sprint_progress = 0
        if active_sprint:
            active_sprint_tickets = list(
                filter_tickets_by_tag(Ticket.objects.filter(sprint=active_sprint), selected_tag)
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
                .order_by("backlog_order", "date_posted", "id")
            )
            configured_capacity = active_sprint.capacity or active_sprint.configured_capacity() or 0
            if configured_capacity:
                active_sprint_progress = min(
                    int((active_sprint.total_story_points() / configured_capacity) * 100),
                    100,
                )

        ctx["epics"] = epics
        ctx["backlog_items"] = backlog_items
        ctx["available_tags"] = available_tags
        ctx["selected_tag"] = selected_tag
        ctx["sprint_blocks"] = self._build_sprint_blocks(project, selected_tag)
        user_is_admin = is_admin(self.request.user)
        ctx["user_is_admin"] = user_is_admin
        ctx["user_can_manage_sprints"] = can_manage_sprints(self.request.user, project)
        if user_is_admin:
            ctx["all_projects"] = Project.objects.order_by("name")
        ctx["backlog_summary"] = {
            "epic_count": epics.count(),
            "backlog_count": len(backlog_items),
            "sprint_count": project.sprints.count(),
            "closed_sprint_count": project.sprints.filter(status=Sprint.STATUS_CLOSED).count(),
        }
        ctx["active_sprint_overview"] = {
            "sprint": active_sprint,
            "tickets": active_sprint_tickets,
            "progress": active_sprint_progress,
        }
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
        messages.info(request, "No active sprint for this project.")
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
