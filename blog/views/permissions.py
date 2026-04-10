from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from ..models import Project, ProjectMember

LEGACY_PROJECT_ROLE_ALIASES = {
    "member",
    "read-only",
    "read_only",
    "admin",
}
PROJECT_CONTRIBUTOR_ROLES = {ProjectMember.ROLE_CONTRIBUTOR}
PROJECT_ROLE_VALUES = {ProjectMember.ROLE_CONTRIBUTOR}


def is_admin(user):
    return user.is_authenticated and user.is_superuser


def can_create_projects(user):
    return is_admin(user)


def get_project_role(user, project):
    if not user.is_authenticated:
        return None
    if is_admin(user):
        return ProjectMember.ROLE_CONTRIBUTOR
    if project.manager_id == user.id:
        return ProjectMember.ROLE_CONTRIBUTOR
    role = (
        ProjectMember.objects.filter(project=project, user=user)
        .values_list("role", flat=True)
        .first()
    )
    if role in LEGACY_PROJECT_ROLE_ALIASES:
        return ProjectMember.ROLE_CONTRIBUTOR
    return role if role in PROJECT_ROLE_VALUES else None


def is_project_read_only(user, project):
    return False


def require_project_admin(user, project):
    if not is_admin(user):
        raise PermissionDenied("Project admin role required.")


def require_project_contributor(user, project):
    if get_project_role(user, project) not in PROJECT_CONTRIBUTOR_ROLES:
        raise PermissionDenied("Contributor role required.")


def can_contribute(user, project=None):
    if project is None:
        return user.is_authenticated
    return get_project_role(user, project) in PROJECT_CONTRIBUTOR_ROLES


def can_create_tickets(user):
    if not user.is_authenticated:
        return False
    if is_admin(user):
        return True
    if Project.objects.filter(manager=user).exists():
        return True
    return ProjectMember.objects.filter(
        user=user,
        role__in=list(LEGACY_PROJECT_ROLE_ALIASES) + [ProjectMember.ROLE_CONTRIBUTOR],
    ).exists()


def can_manage_sprints(user, project):
    return get_project_role(user, project) in PROJECT_CONTRIBUTOR_ROLES


def can_edit_ticket(user, ticket):
    return can_contribute(user, ticket.project)


def is_project_member(user, project):
    return get_project_role(user, project) is not None


def visible_projects(user):
    queryset = Project.objects.all().select_related("manager").prefetch_related("members__user")
    if not user.is_authenticated:
        return queryset.none()
    if is_admin(user):
        return queryset
    return queryset.filter(Q(manager=user) | Q(members__user=user)).distinct()


def project_assignees(project):
    return (
        User.objects.filter(
            Q(project_memberships__project=project) | Q(pk=project.manager_id)
        )
        .distinct()
        .order_by("username")
    )


