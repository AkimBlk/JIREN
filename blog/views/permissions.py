from django.contrib.auth.models import User
from django.db.models import Q

from ..models import Project, ProjectMember, Ticket


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


def can_create_projects(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


def can_contribute(user):
    return user.is_authenticated


def can_manage_sprints(user, project):
    return user.is_authenticated and visible_projects(user).filter(pk=project.pk).exists()


def can_edit_ticket(user, ticket):
    if not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    if ticket.project.manager_id == user.id:
        return True
    if ticket.author_id == user.id:
        return True
    return ProjectMember.objects.filter(project=ticket.project, user=user).exists()


def is_project_member(user, project):
    return (
        user.is_superuser
        or user.is_staff
        or project.manager == user
        or ProjectMember.objects.filter(project=project, user=user).exists()
    )


def visible_projects(user):
    queryset = Project.objects.all().select_related("manager").prefetch_related("members__user")
    if is_admin(user):
        return queryset
    return queryset.filter(members__user=user).distinct()


def project_assignees(project):
    return (
        User.objects.filter(
            Q(project_memberships__project=project) | Q(pk=project.manager_id)
        )
        .distinct()
        .order_by("username")
    )


