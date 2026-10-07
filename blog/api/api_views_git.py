from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Project
from ..services import GitService
from .permissions import has_project_access


def _get_project_with_access(request, project_pk):
    """
    Helper: Get project and verify user has access.

    Returns:
        tuple: (project, Response) or (None, error_response)
    """
    try:
        project = Project.objects.select_related("git_repository").get(pk=project_pk)
    except Project.DoesNotExist:
        return None, Response(
            {"error": "Project not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not has_project_access(request.user, project):
        return None, Response(
            {"error": "Permission denied. You must be a project member."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not hasattr(project, "git_repository") or not project.git_repository:
        return None, Response(
            {"error": "Git repository not configured for this project"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return project, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def git_repository_info(request, project_pk):
    """Retrieve Git repository info and recent commits."""
    project, error = _get_project_with_access(request, project_pk)
    if error:
        return error

    try:
        git_service = GitService(project.git_repository)
        return Response(
            {
                "repository": git_service.get_repository_info(),
                "recent_commits": git_service.get_recent_commits(),
            },
            status=status.HTTP_200_OK,
        )
    except Exception as error:
        return Response(
            {"error": f"Failed to retrieve Git information: {str(error)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def git_repository_branches(request, project_pk):
    """Retrieve Git repository branches."""
    project, error = _get_project_with_access(request, project_pk)
    if error:
        return error

    try:
        git_service = GitService(project.git_repository)
        return Response(
            {"branches": git_service.get_branches()},
            status=status.HTTP_200_OK,
        )
    except Exception as error:
        return Response(
            {"error": f"Failed to retrieve branches: {str(error)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
