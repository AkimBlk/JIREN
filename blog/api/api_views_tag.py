import logging

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Project, ProjectMember, Tag
from .serializers import TagSerializer

logger = logging.getLogger(__name__)


class IsProjectMember:
    def has_project_permission(self, user, project):
        if project.manager_id == user.id:
            return True
        return ProjectMember.objects.filter(project=project, user=user).exists()


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs.get("project_id")
        if not project_id:
            return Tag.objects.none()
        return Tag.objects.filter(project_id=project_id).order_by("name")

    def get_project(self):
        project_id = self.kwargs.get("project_id")
        if not project_id:
            raise ValueError("project_id not in URL kwargs")

        project = get_object_or_404(Project, id=project_id)

        if self.request.user.is_superuser or self.request.user.is_staff:
            return project

        member_exists = ProjectMember.objects.filter(
            project=project, user=self.request.user
        ).exists()
        if project.manager_id != self.request.user.id and not member_exists:
            self.permission_denied(self.request, "You are not a member of this project.")

        return project

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context["project"] = self.get_project()
        except ValueError:
            pass
        except Exception as exc:
            logger.error("Error getting project context: %s", exc, exc_info=True)
        return context

    def _get_project_or_error(self):
        try:
            return self.get_project(), None
        except Exception as exc:
            return None, Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    def list(self, request, *args, **kwargs):
        project, error = self._get_project_or_error()
        if error:
            return error
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        project, error = self._get_project_or_error()
        if error:
            return error
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project=project)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        project, error = self._get_project_or_error()
        if error:
            return error
        tag = get_object_or_404(self.get_queryset(), id=self.kwargs.get("pk"))
        return Response(self.get_serializer(tag).data)

    def destroy(self, request, *args, **kwargs):
        project, error = self._get_project_or_error()
        if error:
            return error
        if project.manager_id != request.user.id and not request.user.is_staff:
            return Response(
                {"detail": "Only project managers can delete tags."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tag = get_object_or_404(self.get_queryset(), id=self.kwargs.get("pk"))
        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
