from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import DetailView

from ..models import Project, Sprint, Ticket
from .permissions import visible_projects

PERCENTAGE_MULTIPLIER = 100
DECIMAL_PRECISION = 2


class ProjectStatisticsView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "blog/project_statistics.html"
    context_object_name = "project"

    def get_queryset(self):
        return visible_projects(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        closed_sprints = list(
            self.object.sprints.filter(status=Sprint.STATUS_CLOSED)
            .prefetch_related("tickets")
            .order_by("start_date")
        )

        velocity_labels = []
        velocity_values = []
        consumption_values = []

        for sprint in closed_sprints:
            done_points = self._done_story_points(sprint)
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

        ctx["velocity_labels"] = velocity_labels
        ctx["velocity_values"] = velocity_values
        ctx["consumption_values"] = consumption_values
        ctx["burndown"] = burndown
        ctx["selected_sprint"] = selected_sprint
        ctx["has_statistics_data"] = bool(closed_sprints)

        return ctx

    def _done_story_points(self, sprint):
        return (
            sprint.tickets.filter(status=Ticket.STATUS_DONE)
            .aggregate(total=Sum("story_points"))["total"]
            or 0
        )

    def _burndown_data(self, sprint):
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

        # Build an honest approximation: sprint starts at total_points and
        # declines linearly to remaining at the end (historical snapshots are
        # not stored; this avoids the misleading flat-line artefact).
        burn_step = (total_points - remaining) / (day_count - 1) if day_count > 1 else 0
        for i in range(day_count):
            ideal.append(round(total_points - (ideal_step * i), DECIMAL_PRECISION))
            actual.append(round(total_points - (burn_step * i), DECIMAL_PRECISION))

        return {
            "labels": [d.strftime("%d/%m") for d in days],
            "ideal": ideal,
            "actual": actual,
        }
