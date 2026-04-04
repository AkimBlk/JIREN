"""
DRF Serializers for blog app models (Tags, Tickets, Projects).
"""
from rest_framework import serializers
from django.db.models import Count

from ..models import Tag, Ticket, Project


class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for project-scoped tags.
    
    Provides:
    - Basic tag info (id, name, normalized_name)
    - Count of associated tickets
    - Read-only computed fields
    """
    ticket_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ["id", "name", "normalized_name", "ticket_count", "project"]
        read_only_fields = ["id", "normalized_name", "project", "ticket_count"]
    
    def get_ticket_count(self, obj):
        """Return the number of tickets using this tag."""
        return obj.tickets.count()
    
    def create(self, validated_data):
        """Create a new tag, ensuring it belongs to the correct project."""
        # Project comes from context (passed by view)
        project = self.context.get("project")
        if not project:
            raise serializers.ValidationError("Project context is required to create a tag.")
        
        validated_data["project"] = project
        return super().create(validated_data)
    
    def validate_name(self, value):
        """
        Validate tag name uniqueness within the project.
        Allow case-insensitive duplicates check.
        """
        from ..models.tag import normalize_tag_name
        
        project = self.context.get("project")
        normalized = normalize_tag_name(value)
        
        # Check if tag already exists in this project (case-insensitive)
        existing = Tag.objects.filter(
            project=project,
            normalized_name=normalized
        ).exclude(pk=self.instance.pk if self.instance else None)
        
        if existing.exists():
            raise serializers.ValidationError(
                f"A tag with this name already exists in this project."
            )
        
        return value


class TicketTagUpdateSerializer(serializers.Serializer):
    """
    Serializer for adding/removing tags to/from a ticket.
    Accepts either tag_id or tag_name.
    """
    tag_id = serializers.IntegerField(required=False, allow_null=True)
    tag_name = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Ensure either tag_id or tag_name is provided."""
        if not data.get("tag_id") and not data.get("tag_name"):
            raise serializers.ValidationError(
                "Either tag_id or tag_name must be provided."
            )
        return data


class TicketListSerializer(serializers.ModelSerializer):
    """
    Lightweight ticket serializer for list views.
    Includes tag information for display.
    """
    tags = TagSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source="author.username", read_only=True)
    assignee_name = serializers.CharField(source="assignee.username", read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            "id", "title", "status", "priority", "issue_type",
            "author_name", "assignee_name", "tags",
            "story_points", "date_posted"
        ]
        read_only_fields = fields


class TicketDetailSerializer(serializers.ModelSerializer):
    """
    Full ticket serializer with all details and relationships.
    """
    tags = TagSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source="author.username", read_only=True)
    assignee_name = serializers.CharField(source="assignee.username", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            "id", "title", "description", "status", "priority", "issue_type",
            "author_name", "assignee_name", "project_name",
            "tags", "story_points", "remaining_load", "initial_load",
            "date_posted", "sprint"
        ]
        read_only_fields = [
            "id", "author_name", "project_name", "tags",
            "date_posted"
        ]


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for project info (used in context)."""
    manager_name = serializers.CharField(source="manager.username", read_only=True)
    
    class Meta:
        model = Project
        fields = ["id", "name", "code_prefix", "manager_name"]
        read_only_fields = ["id", "manager_name"]
