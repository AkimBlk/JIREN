from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, IntegerField, Value, When
from django.views.generic import ListView

from ..models import Sprint, Tag, Ticket
from .permissions import is_admin, visible_projects
from .queries import filter_tickets_by_tag, resolve_tag_filter


class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = "blog/home.html"
    context_object_name = "tickets"

    def get_selected_project(self):
        projects = visible_projects(self.request.user).order_by("name")
        project_id = self.request.GET.get("project")
        if project_id:
            selected = projects.filter(pk=project_id).first()
            if selected:
                return selected
        return projects.first()

    def _get_active_sprint(self, project):
        return (
            Sprint.objects.filter(project=project, status=Sprint.STATUS_ACTIVE)
            .order_by("start_date", "id")
            .first()
        )

    def get_queryset(self):
        project = self.get_selected_project()
        if not project:
            self.available_tags = Tag.objects.none()
            self.selected_tag = None
            return Ticket.objects.none()

        active_sprint = self._get_active_sprint(project)
        if not active_sprint:
            self.available_tags = Tag.objects.none()
            self.selected_tag = None
            return Ticket.objects.none()

        base_queryset = Ticket.objects.filter(sprint=active_sprint)
        self.available_tags, self.selected_tag = resolve_tag_filter(self.request, base_queryset)
        filtered = filter_tickets_by_tag(base_queryset, self.selected_tag)

        return (
            filtered.select_related("project", "epic", "assignee", "sprint")
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
            .order_by("priority_order", "-date_posted", "id")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        selected_project = self.get_selected_project()
        ctx["projects"] = visible_projects(self.request.user).order_by("name")
        ctx["selected_project"] = selected_project
        ctx["active_sprint"] = self._get_active_sprint(selected_project) if selected_project else None
        ctx["available_tags"] = getattr(self, "available_tags", Tag.objects.none())
        ctx["selected_tag"] = getattr(self, "selected_tag", None)
        ctx["title"] = "Sprint actif"
        return ctx


class AllTicketsListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = "blog/all_tickets.html"
    context_object_name = "tickets"

    def get_queryset(self):
        base = (
            Ticket.objects.all()
            if is_admin(self.request.user)
            else Ticket.objects.filter(project__in=visible_projects(self.request.user))
        )
        self.available_tags, self.selected_tag = resolve_tag_filter(self.request, base)
        return (
            filter_tickets_by_tag(base, self.selected_tag)
            .select_related("project", "sprint", "author", "assignee")
            .prefetch_related("tags")
            .order_by("-date_posted")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["available_tags"] = getattr(self, "available_tags", Tag.objects.none())
        ctx["selected_tag"] = getattr(self, "selected_tag", None)
        return ctx


