from django.shortcuts import render

from .analytics_view import AnalyticsView
from .project import (
    ProjectBacklogView,
    ProjectCreateView,
    ProjectDeleteView,
    ProjectDetailView,
    ProjectHomeView,
    ProjectUpdateView,
    delete_projects,
    project_active_sprint,
)
from .sprint import (
    SprintAdminIndexView,
    SprintUpdateView,
    delete_sprint,
    move_backlog_ticket,
    sprint_admin,
    sprint_close,
    sprint_start,
    update_sprint_status,
)
from .tag import api_project_tags, api_ticket_add_tag, api_ticket_remove_tag, project_tags
from .ticket import (
    AllTicketsListView,
    TicketCreateView,
    TicketDeleteView,
    TicketDetailView,
    TicketListView,
    TicketUpdateView,
    delete_ticket_attachment,
    update_ticket_remaining_load,
    update_ticket_status,
)

__all__ = [
    "about",
    "AllTicketsListView",
    "AnalyticsView",
    "ProjectBacklogView",
    "ProjectCreateView",
    "ProjectDeleteView",
    "ProjectDetailView",
    "ProjectHomeView",
    "ProjectUpdateView",
    "SprintAdminIndexView",
    "SprintUpdateView",
    "TicketCreateView",
    "TicketDeleteView",
    "TicketDetailView",
    "TicketListView",
    "TicketUpdateView",
    "api_project_tags",
    "api_ticket_add_tag",
    "api_ticket_remove_tag",
    "delete_projects",
    "delete_sprint",
    "delete_ticket_attachment",
    "move_backlog_ticket",
    "project_active_sprint",
    "project_tags",
    "sprint_admin",
    "sprint_close",
    "sprint_start",
    "update_sprint_status",
    "update_ticket_remaining_load",
    "update_ticket_status",
]


def about(request):
    return render(request, "blog/about.html", {"title": "About"})
