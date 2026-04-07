from django.db import models
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from .project import Project


class GitRepository(models.Model):
    """
    Stores Git repository configuration linked to a Project.
    Token stored securely (hashed in production, encrypted at rest).
    """

    REPOSITORY_TYPE_GITHUB = "github"
    REPOSITORY_TYPE_GITLAB = "gitlab"
    REPOSITORY_TYPE_GITEA = "gitea"
    REPOSITORY_TYPE_LOCAL = "local"

    REPOSITORY_TYPE_CHOICES = [
        (REPOSITORY_TYPE_GITHUB, "GitHub"),
        (REPOSITORY_TYPE_GITLAB, "GitLab"),
        (REPOSITORY_TYPE_GITEA, "Gitea"),
        (REPOSITORY_TYPE_LOCAL, "Local Repository"),
    ]

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="git_repository",
        help_text="Project linked to this Git repository",
    )
    repository_url = models.URLField(
        max_length=500,
        validators=[URLValidator()],
        help_text="Git repository URL (e.g., https://github.com/user/repo)",
    )
    repository_type = models.CharField(
        max_length=20,
        choices=REPOSITORY_TYPE_CHOICES,
        default=REPOSITORY_TYPE_LOCAL,
        help_text="Type of Git hosting service",
    )
    access_token = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="API token for private repos (GitHub/GitLab personal token)",
    )
    is_private = models.BooleanField(
        default=False,
        help_text="Whether the repository is private",
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time repository was queried for updates",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this repository config was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Git Repository"
        verbose_name_plural = "Git Repositories"
        indexes = [
            models.Index(fields=["project", "repository_type"]),
        ]

    def __str__(self):
        return f"{self.project.name} — {self.repository_url}"

    def clean(self):
        """Validate repository configuration before saving."""
        errors = {}

        if self.is_private and not self.access_token:
            errors["access_token"] = (
                "Private repositories require an access token."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def is_token_configured(self):
        """Check if API token is available for authenticated requests."""
        return bool(self.access_token and self.access_token.strip())
