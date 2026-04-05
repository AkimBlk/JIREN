from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import DetailView

from ..models import Project, Sprint, Ticket
from .permissions import visible_projects


class ProjectStatisticsView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "blog/project_statistics.html"
    context_object_name = "project"

    def get_queryset(self):
        return visible_projects(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object

        closed_sprints = list(
            project.sprints.filter(status=Sprint.STATUS_CLOSED)
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
            if capacity:
                consumption = round((done_points / capacity) * 100, 2)

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

        return ctx

    def _done_story_points(self, sprint):
        return (
            sprint.tickets.filter(status=Ticket.STATUS_DONE)
            .aggregate(total=Sum("story_points"))["total"]
            or 0
        )

    def _burndown_data(self, sprint):

        tickets = list(sprint.tickets.all())

        days = []
        day = sprint.start_date

        while day <= sprint.end_date:
            days.append(day)
            day += timedelta(days=1)

        total_points = sum(t.story_points or 0 for t in tickets)

        ideal = []
        actual = []

        remaining = total_points

        for i, day in enumerate(days):

            ideal_remaining = total_points - ((total_points / (len(days)-1)) * i) if len(days) > 1 else 0
            ideal.append(round(ideal_remaining, 2))

            done_today = sum(
                t.story_points or 0
                for t in tickets
                if t.status == Ticket.STATUS_DONE
            )

            remaining = max(total_points - done_today, 0)
            actual.append(remaining)

        return {
            "labels": [d.strftime("%d/%m") for d in days],
            "ideal": ideal,
            "actual": actual,
        }