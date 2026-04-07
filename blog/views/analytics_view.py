from datetime import timedelta
from typing import Dict, List, Optional

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import QuerySet, Sum
from django.views.generic import TemplateView

from ..models import Project, Sprint, Ticket

PERCENTAGE_MULTIPLIER = 100
DECIMAL_PRECISION = 2


class AnalyticsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Display analytics dashboard with per-project filtering."""

    template_name = "blog/analytics_dashboard.html"

    def test_func(self) -> bool:
        """Only staff and superusers can access analytics."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs) -> Dict:
        ctx = super().get_context_data(**kwargs)

        # Extract project filter from query params
        project_id = self.request.GET.get("project_id", None)

        # Get all projects and sprints
        all_projects = self._get_projects()
        sprints = self._get_sprints(project_id)

        # Calculate analytics metrics
        analytics = self._calculate_analytics(sprints)

        # Determine selected project
        selected_project = None
        if project_id:
            selected_project = all_projects.filter(pk=project_id).first()

        ctx.update(
            {
                "all_projects": all_projects,
                "selected_project": selected_project,
                "projects_count": Project.objects.count(),
                "sprints_count": len(sprints),
                **analytics,
            }
        )

        return ctx

    def _get_projects(self) -> QuerySet:
        """Get all projects ordered by name."""
        return Project.objects.all().order_by("name")

    def _get_sprints(self, project_id: Optional[int] = None) -> List[Sprint]:
        """Get closed sprints, optionally filtered by project."""
        query = (
            Sprint.objects.filter(status=Sprint.STATUS_CLOSED)
            .select_related("project")
            .prefetch_related("tickets")
            .order_by("start_date")
        )

        if project_id:
            query = query.filter(project_id=project_id)

        return list(query)

    def _calculate_analytics(self, sprints: List[Sprint]) -> Dict:
        """Calculate velocity, consumption, and burndown metrics."""
        velocity_labels = []
        velocity_values = []
        consumption_values = []

        for sprint in sprints:
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

        selected_sprint = sprints[-1] if sprints else None
        burndown = self._burndown_data(selected_sprint) if selected_sprint else None

        return {
            "velocity_labels": velocity_labels,
            "velocity_values": velocity_values,
            "consumption_values": consumption_values,
            "burndown": burndown,
            "selected_sprint": selected_sprint,
        }

    def _calculate_done_story_points(self, sprint: Sprint) -> int:
        """Calculate total story points marked as done in a sprint."""
        return (
            sprint.tickets.filter(status=Ticket.STATUS_DONE).aggregate(
                total=Sum("story_points")
            )["total"]
            or 0
        )

    def _burndown_data(self, sprint: Sprint) -> Optional[Dict]:
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
            t.story_points or 0 for t in tickets if t.status == Ticket.STATUS_DONE
        )
        remaining = max(total_points - done_so_far, 0)

        burn_step = (
            (total_points - remaining) / (day_count - 1) if day_count > 1 else 0
        )
        for i in range(day_count):
            ideal.append(
                round(total_points - (ideal_step * i), DECIMAL_PRECISION)
            )
            actual.append(
                round(total_points - (burn_step * i), DECIMAL_PRECISION)
            )

        return {
            "labels": [d.strftime("%d/%m") for d in days],
            "ideal": ideal,
            "actual": actual,
        }
