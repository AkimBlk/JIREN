from django.urls import path

from . import views
from .views import (
    AllTicketsListView,
    ProjectBacklogView,
    ProjectCreateView,
    ProjectDeleteView,
    ProjectDetailView,
    ProjectHomeView,
    ProjectUpdateView,
    SprintAdminIndexView,
    TicketCreateView,
    TicketDeleteView,
    TicketDetailView,
    TicketListView,
    TicketUpdateView,
    api_project_tags,
    api_ticket_add_tag,
    api_ticket_remove_tag,
    move_backlog_ticket,
    project_active_sprint,
    project_tags,
    sprint_admin,
    sprint_close,
    sprint_start,
)

urlpatterns = [
    path("", ProjectHomeView.as_view(), name="blog-home"),
    path("kanban/", TicketListView.as_view(), name="kanban"),
    path("ticket/<int:pk>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("ticket/new/", TicketCreateView.as_view(), name="ticket-create"),
    path("ticket/<int:pk>/update/", TicketUpdateView.as_view(), name="ticket-update"),
    path("ticket/<int:pk>/delete/", TicketDeleteView.as_view(), name="ticket-delete"),
    path("ticket/attachment/<int:pk>/delete/", views.delete_ticket_attachment, name="ticket-attachment-delete"),
    path("ticket/<int:pk>/status/", views.update_ticket_status, name="ticket-update-status"),
    path(
    "ticket/<int:pk>/remaining-load/",
    views.update_ticket_remaining_load,
    name="ticket-update-remaining-load",
    ),

    # API Endpoints for tags and ticket operations
    path("api/projects/<int:pk>/tags/", api_project_tags, name="api-project-tags"),
    path("api/tickets/<int:pk>/tags/add/", api_ticket_add_tag, name="api-ticket-add-tag"),
    path("api/tickets/<int:pk>/tags/remove/", api_ticket_remove_tag, name="api-ticket-remove-tag"),

    path("tickets/", AllTicketsListView.as_view(), name="all-tickets"),

    path("project/new/", ProjectCreateView.as_view(), name="project-create"),
    path("project/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("project/<int:pk>/update/", ProjectUpdateView.as_view(), name="project-update"),
    path("project/<int:pk>/delete/", ProjectDeleteView.as_view(), name="project-delete"),
    path("project/<int:pk>/backlog/", ProjectBacklogView.as_view(), name="project-backlog"),
    path("project/<int:pk>/active-sprint/", project_active_sprint, name="project-active-sprint"),
    path("project/<int:pk>/tags/", project_tags, name="project-tags"),

    path(
        "ticket/<int:pk>/backlog/move/<str:direction>/",
        move_backlog_ticket,
        name="move-backlog-ticket",
    ),

    path("sprints/admin/", SprintAdminIndexView.as_view(), name="sprint-admin-index"),
    path("project/<int:pk>/sprints/admin/", sprint_admin, name="sprint-admin"),
    path("sprint/<int:pk>/status/", views.update_sprint_status, name="sprint-update-status"),
    path("sprint/<int:pk>/start/", sprint_start, name="sprint-start"),
    path("sprint/<int:pk>/close/", sprint_close, name="sprint-close"),
    path("sprints/<int:pk>/delete/", views.delete_sprint, name="sprint-delete"),
    path("sprints/<int:pk>/edit/", views.SprintUpdateView.as_view(), name="sprint-update"),
    path("projects/delete/", views.delete_projects, name="project-delete-multiple"),
]