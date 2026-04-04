from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q

from ..models import Project, ProjectMember, Sprint, SprintUserCapacity, Tag, Ticket
from .permissions import is_admin, project_assignees, visible_projects


def ticket_form_project_data(user):
    projects = visible_projects(user).order_by("name").prefetch_related(
        Prefetch("sprints", queryset=Sprint.objects.order_by("start_date", "id")),
        Prefetch(
            "tickets",
            queryset=Ticket.objects.filter(issue_type=Ticket.ISSUE_TYPE_EPIC).order_by("title"),
            to_attr="ticket_form_epics",
        ),
        Prefetch(
            "tickets",
            queryset=Ticket.objects.order_by("title", "id"),
            to_attr="ticket_form_linkables",
        ),
        Prefetch(
            "members",
            queryset=ProjectMember.objects.select_related("user").order_by("user__username"),
            to_attr="ticket_form_memberships",
        ),
    )

    project_data = {}
    for project in projects:
        assignees = {m.user_id: m.user.username for m in project.ticket_form_memberships}
        if project.manager_id:
            assignees[project.manager_id] = project.manager.username

        project_data[str(project.pk)] = {
            "sprints": [
                {"value": str(sprint.pk), "label": sprint.name}
                for sprint in project.sprints.exclude(status=Sprint.STATUS_CLOSED)
            ],
            "epics": [
                {"value": str(epic.pk), "label": epic.title}
                for epic in project.ticket_form_epics
            ],
            "linkables": [
                {"value": str(t.pk), "label": f"#{t.pk} - {t.title}"}
                for t in project.ticket_form_linkables
            ],
            "assignees": [
                {"value": str(uid), "label": uname}
                for uid, uname in sorted(assignees.items(), key=lambda item: item[1].lower())
            ],
        }

    return project_data


def capacity_rows(project, post_data=None, sprint=None):
    existing = {}
    if sprint is not None:
        existing = {item.user_id: item.capacity for item in sprint.user_capacities.select_related("user")}

    rows = []
    for user in project_assignees(project):
        input_name = f"capacity_user_{user.pk}"
        value = post_data.get(input_name, "") if post_data is not None else existing.get(user.pk, "")
        rows.append({"user": user, "input_name": input_name, "value": value})

    return rows


def save_sprint_user_capacities(sprint, post_data):
    sprint.user_capacities.all().delete()

    if sprint.capacity_mode == Sprint.CAPACITY_MODE_GLOBAL:
        return

    created_count = 0
    for row in capacity_rows(sprint.project, post_data=post_data):
        raw_value = str(row["value"]).strip()
        if not raw_value:
            continue

        try:
            capacity_value = int(raw_value)
        except ValueError:
            raise ValidationError("Each user capacity must be a whole number.")

        if capacity_value <= 0:
            raise ValidationError("Each user capacity must be greater than 0.")

        SprintUserCapacity.objects.create(sprint=sprint, user=row["user"], capacity=capacity_value)
        created_count += 1

    if created_count == 0:
        raise ValidationError("Configure at least one user capacity in per-user mode.")


def project_backlog_queryset(project):
    return (
        Ticket.objects.filter(
            project=project,
            issue_type__in=[Ticket.ISSUE_TYPE_STORY, Ticket.ISSUE_TYPE_BUG],
        )
        .filter(Q(sprint__isnull=True) | ~Q(sprint__status=Sprint.STATUS_ACTIVE))
        .select_related("epic", "assignee", "sprint")
        .prefetch_related("tags")
        .order_by("backlog_order", "date_posted", "id")
    )


def available_tags_for_tickets(ticket_queryset):
    return Tag.objects.filter(tickets__in=ticket_queryset).distinct().order_by("name")


def resolve_tag_filter(request, ticket_queryset):
    available_tags = available_tags_for_tickets(ticket_queryset)
    selected_tag_id = request.GET.get("tag")
    selected_tag = available_tags.filter(pk=selected_tag_id).first() if selected_tag_id else None
    return available_tags, selected_tag


def filter_tickets_by_tag(ticket_queryset, selected_tag):
    if not selected_tag:
        return ticket_queryset
    return ticket_queryset.filter(tags=selected_tag).distinct()


def project_linkable_tickets(project, exclude_ticket=None):
    queryset = project.tickets.order_by("title", "id")
    if exclude_ticket is not None:
        queryset = queryset.exclude(pk=exclude_ticket.pk)
    return queryset


