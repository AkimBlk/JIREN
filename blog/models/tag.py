"""
Tag model for organizing and classifying tickets within projects.
Follows Clean Code: project-scoped tags, case-insensitive uniqueness.
"""
from django.db import models
from django.core.exceptions import ValidationError
from .core import Project


def normalize_tag_name(name):
    """Convert tag name to normalized form: trim + lowercase."""
    return " ".join(str(name).split()).casefold()


class Tag(models.Model):
    """
    Project-scoped tags for organizing tickets.
    
    Uniqueness enforced by (project, normalized_name) to allow
    identical tag names in different projects.
    """
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tags",
        help_text="Project this tag belongs to.",
    )
    name = models.CharField(
        max_length=50,
        help_text="Display name (may contain spaces).",
    )
    normalized_name = models.CharField(
        max_length=50,
        editable=False,
        help_text="Internal normalized form (lowercase, trimmed).",
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "normalized_name"],
                name="unique_tag_per_project",
            )
        ]

    def clean(self):
        super().clean()
        self.name = " ".join(self.name.split())
        
        if not self.name:
            raise ValidationError({"name": "Tag name required."})
        
        self.normalized_name = normalize_tag_name(self.name)
        
        # Validate tags stay in their project
        if self.pk:
            tickets_other_projects = self.tickets.exclude(
                project=self.project
            )
            if tickets_other_projects.exists():
                raise ValidationError(
                    {"project": "Tag already used in other projects."}
                )

    def save(self, *args, **kwargs):
        self.name = " ".join(self.name.split())
        self.normalized_name = normalize_tag_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
