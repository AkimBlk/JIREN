from django.urls import reverse

from .models import Sprint, Ticket
from .views.permissions import visible_projects


PROJECT_PK_URLS = {
    "project-list",
    "project-detail",
    "project-backlog",
    "project-update",
    "project-delete",
    "project-active-sprint",
    "project-statistics",
    "project-tags",
    "sprint-admin",
}

SPRINT_PK_URLS = {
    "sprint-list",
    "sprint-create",
    "sprint-detail",
    "sprint-kanban",
    "sprint-update-status",
    "sprint-start",
    "sprint-close",
    "sprint-delete",
    "sprint-update",
}

TICKET_PK_URLS = {
    "ticket-detail",
    "ticket-update",
    "ticket-delete",
    "ticket-update-status",
    "ticket-update-remaining-load",
}


def shell_navigation(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}

    projects = visible_projects(request.user).order_by("name")
    project_id = _resolve_shell_project_id(request, projects)

    if not project_id:
        return {
            "shell_backlog_url": reverse("project-list"),
            "shell_kanban_url": reverse("kanban"),
            "shell_sprint_url": reverse("project-list"),
        }

    return {
        "shell_backlog_url": reverse("project-backlog", kwargs={"pk": project_id}),
        "shell_kanban_url": f"{reverse('kanban')}?project={project_id}",
        "shell_sprint_url": reverse("sprint-list", kwargs={"pk": project_id}),
    }


def _resolve_shell_project_id(request, projects):
    project_id = request.GET.get("project")
    if project_id and projects.filter(pk=project_id).exists():
        return project_id

    resolver_match = getattr(request, "resolver_match", None)
    if not resolver_match:
        return projects.values_list("id", flat=True).first()

    url_name = resolver_match.url_name
    project_pk = resolver_match.kwargs.get("pk")
    sprint_pk = resolver_match.kwargs.get("spk") or project_pk
    ticket_pk = resolver_match.kwargs.get("tpk")

    if url_name in PROJECT_PK_URLS and project_pk and projects.filter(pk=project_pk).exists():
        return project_pk

    if url_name in SPRINT_PK_URLS:
        if project_pk and projects.filter(pk=project_pk).exists():
            return project_pk
        if sprint_pk:
            return Sprint.objects.filter(
                pk=sprint_pk,
                project__in=projects,
            ).values_list("project_id", flat=True).first()

    if url_name in TICKET_PK_URLS:
        if project_pk and ticket_pk and projects.filter(pk=project_pk).exists():
            return project_pk
        if ticket_pk:
            return Ticket.objects.filter(
                pk=ticket_pk,
                project__in=projects,
            ).values_list("project_id", flat=True).first()
        if project_pk:
            return Ticket.objects.filter(
                pk=project_pk,
                project__in=projects,
            ).values_list("project_id", flat=True).first()

    return projects.values_list("id", flat=True).first()
