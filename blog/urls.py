from django.urls import path
from django.views.generic import RedirectView
from .views.statistics import ProjectStatisticsView
from .views.git_setup import GitRepositoryCreateView, GitRepositoryUpdateView
from .views import AnalyticsView

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
    link_commit_to_ticket,
    project_active_sprint,
    project_tags,
    reorder_backlog,
    reorder_sprint_tickets,
    sprint_admin,
    sprint_close,
    sprint_start,
)

LEGACY_REDIRECT_PERMANENT = False

urlpatterns = [
    # Canonical HELB routes
    path(
        "",
        RedirectView.as_view(
            pattern_name="project-list",
            permanent=LEGACY_REDIRECT_PERMANENT,
        ),
    ),
    path("projects/", ProjectHomeView.as_view(), name="project-list"),
    path("projects/", ProjectHomeView.as_view(), name="blog-home"),
    path("help/", views.help_page, name="help"),
    path("projects/create/", ProjectCreateView.as_view(), name="project-create"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<int:pk>/edit/", ProjectUpdateView.as_view(), name="project-update"),
    path("projects/<int:pk>/delete/", ProjectDeleteView.as_view(), name="project-delete"),
    path("projects/<int:pk>/tickets/new/", TicketCreateView.as_view(), name="ticket-create"),
    path(
        "projects/<int:pk>/tickets/<int:tpk>/",
        TicketDetailView.as_view(pk_url_kwarg="tpk"),
        name="ticket-detail",
    ),
    path(
        "projects/<int:pk>/tickets/<int:tpk>/edit/",
        TicketUpdateView.as_view(pk_url_kwarg="tpk"),
        name="ticket-update",
    ),
    path(
        "projects/<int:pk>/tickets/<int:tpk>/delete/",
        TicketDeleteView.as_view(pk_url_kwarg="tpk"),
        name="ticket-delete",
    ),
    path("projects/<int:pk>/sprints/", sprint_admin, name="sprint-list"),
    path("projects/<int:pk>/sprints/create/", sprint_admin, name="sprint-create"),
    path(
        "projects/<int:pk>/sprints/<int:spk>/",
        views.SprintUpdateView.as_view(pk_url_kwarg="spk"),
        name="sprint-detail",
    ),
    path("projects/<int:pk>/sprints/<int:spk>/start/", sprint_start, name="sprint-start"),
    path("projects/<int:pk>/sprints/<int:spk>/close/", sprint_close, name="sprint-close"),
    path("projects/<int:pk>/sprints/<int:spk>/kanban/", TicketListView.as_view(), name="sprint-kanban"),

    # Legacy project aliases (temporary)
    path(
        "project/new/",
        RedirectView.as_view(
            pattern_name="project-create",
            permanent=LEGACY_REDIRECT_PERMANENT,
        ),
        name="project-create-legacy",
    ),
    path(
        "project/<int:pk>/",
        RedirectView.as_view(
            pattern_name="project-detail",
            permanent=LEGACY_REDIRECT_PERMANENT,
        ),
        name="project-detail-legacy",
    ),
    path(
        "project/<int:pk>/update/",
        RedirectView.as_view(
            pattern_name="project-update",
            permanent=LEGACY_REDIRECT_PERMANENT,
        ),
        name="project-update-legacy",
    ),
    path(
        "project/<int:pk>/delete/",
        RedirectView.as_view(
            pattern_name="project-delete",
            permanent=LEGACY_REDIRECT_PERMANENT,
        ),
        name="project-delete-legacy",
    ),

    # Legacy routes kept for compatibility
    path("kanban/", TicketListView.as_view(), name="kanban"),
    path("ticket/<int:pk>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("ticket/new/", TicketCreateView.as_view(), name="ticket-create"),
    path("ticket/<int:pk>/update/", TicketUpdateView.as_view(), name="ticket-update"),
    path("ticket/<int:pk>/delete/", TicketDeleteView.as_view(), name="ticket-delete"),
    path("ticket/<int:pk>/link-commit/", link_commit_to_ticket, name="ticket-link-commit"),
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
    path("project/<int:pk>/backlog/", ProjectBacklogView.as_view(), name="project-backlog"),
    path("project/<int:pk>/active-sprint/", project_active_sprint, name="project-active-sprint"),
    path("project/<int:pk>/tags/", project_tags, name="project-tags"),

    path(
        "ticket/<int:pk>/backlog/move/<str:direction>/",
        move_backlog_ticket,
        name="move-backlog-ticket",
    ),
    path(
        "project/<int:project_pk>/backlog/reorder/",
        reorder_backlog,
        name="backlog-reorder",
    ),
    path("sprint/<int:sprint_pk>/tickets/reorder/", reorder_sprint_tickets, name="sprint-tickets-reorder"),

    path("sprints/admin/", SprintAdminIndexView.as_view(), name="sprint-admin-index"),
    path("project/<int:pk>/sprints/admin/", sprint_admin, name="sprint-admin"),
    path("sprint/<int:pk>/status/", views.update_sprint_status, name="sprint-update-status"),
    path("sprint/<int:pk>/start/", sprint_start, name="sprint-start"),
    path("sprint/<int:pk>/close/", sprint_close, name="sprint-close"),
    path("sprints/<int:pk>/delete/", views.delete_sprint, name="sprint-delete"),
    path("sprints/<int:pk>/edit/", views.SprintUpdateView.as_view(), name="sprint-update"),
    path("projects/delete/", views.delete_projects, name="project-delete-multiple"),
    path("project/<int:pk>/statistics/", ProjectStatisticsView.as_view(), name="project-statistics"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),

    # Git repository setup
    path("project/<int:project_pk>/git/add/", GitRepositoryCreateView.as_view(), name="git-setup-create"),
    path("project/<int:project_pk>/git/edit/", GitRepositoryUpdateView.as_view(), name="git-setup-update"),
]
