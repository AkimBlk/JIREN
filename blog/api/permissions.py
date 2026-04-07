from ..models import ProjectMember


def has_project_access(user, project) -> bool:
    """
    Check if user has access to project.

    Access is granted if:
    - User is the project manager/owner
    - User is a project member

    Args:
        user: Django User instance
        project: Project instance

    Returns:
        bool: True if user has access, False otherwise
    """
    if user == project.manager:
        return True
    return ProjectMember.objects.filter(
        project=project,
        user=user,
    ).exists()
