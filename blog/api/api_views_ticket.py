from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets

from ..models import ProjectMember, Tag, Ticket
from ..models.tag import normalize_tag_name
from .serializers import TagSerializer, TicketTagUpdateSerializer


class TicketTagViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_ticket(self, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id)
        project = ticket.project
        is_member = (
            self.request.user.is_superuser
            or self.request.user.is_staff
            or project.manager_id == self.request.user.id
            or ProjectMember.objects.filter(project=project, user=self.request.user).exists()
        )
        return ticket if is_member else None

    def _ticket_or_denied(self, ticket_id):
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None, Response(
                {"detail": "Ticket not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return ticket, None

    def _resolve_tag(self, ticket, validated_data):
        tag_id = validated_data.get("tag_id")
        tag_name = validated_data.get("tag_name")
        if tag_id:
            return get_object_or_404(Tag.objects.filter(project=ticket.project), id=tag_id)
        # Create tag if it doesn't exist (use get_or_create, not get_object_or_404)
        tag, _ = Tag.objects.get_or_create(
            name=tag_name,
            project=ticket.project,
        )
        return tag

    def add_tag(self, request, ticket_id=None):
        ticket, error = self._ticket_or_denied(ticket_id)
        if error:
            return error

        serializer = TicketTagUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                tag = self._resolve_tag(ticket, serializer.validated_data)
                if ticket.tags.filter(id=tag.id).exists():
                    return Response(
                        {"detail": f"Tag '{tag.name}' is already on this ticket.", "tags": TagSerializer(ticket.tags.all(), many=True).data},
                        status=status.HTTP_200_OK,
                    )
                ticket.tags.add(tag)
                return Response(
                    {"detail": f"Tag '{tag.name}' added.", "tags": TagSerializer(ticket.tags.all(), many=True).data},
                    status=status.HTTP_200_OK,
                )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def remove_tag(self, request, ticket_id=None):
        ticket, error = self._ticket_or_denied(ticket_id)
        if error:
            return error

        serializer = TicketTagUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                tag = self._resolve_tag(ticket, serializer.validated_data)
                if not ticket.tags.filter(id=tag.id).exists():
                    return Response({"detail": "Tag not on ticket."}, status=status.HTTP_400_BAD_REQUEST)
                ticket.tags.remove(tag)
                return Response(
                    {"detail": f"Tag '{tag.name}' removed.", "tags": TagSerializer(ticket.tags.all(), many=True).data},
                    status=status.HTTP_200_OK,
                )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def list_tags(self, request, ticket_id=None):
        ticket, error = self._ticket_or_denied(ticket_id)
        if error:
            return error
        serializer = TagSerializer(ticket.tags.all(), many=True)
        return Response(serializer.data)
