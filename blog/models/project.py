from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Project(models.Model):
    WORKLOAD_UNIT_MAN_DAYS = "MAN_DAYS"
    WORKLOAD_UNIT_MAN_HOURS = "MAN_HOURS"
    WORKLOAD_UNIT_STORY_POINTS = "STORY_POINTS"
    WORKLOAD_UNIT_CHOICES = [
        (WORKLOAD_UNIT_MAN_DAYS, "Man-days"),
        (WORKLOAD_UNIT_MAN_HOURS, "Man-hours"),
        (WORKLOAD_UNIT_STORY_POINTS, "Story points"),
    ]

    CAPACITY_MODE_GLOBAL = "GLOBAL"
    CAPACITY_MODE_PER_USER = "PER_USER"
    CAPACITY_MODE_CHOICES = [
        (CAPACITY_MODE_GLOBAL, "Global capacity"),
        (CAPACITY_MODE_PER_USER, "Capacity per user"),
    ]

    code_prefix = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9][A-Z0-9_-]*$",
                message="Project code: uppercase, numbers, underscore, hyphen only.",
            )
        ],
        help_text="Unique project prefix (e.g., 'CRM').",
    )
    name = models.CharField(max_length=100)
    description = models.TextField()
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    workload_unit = models.CharField(
        max_length=20,
        choices=WORKLOAD_UNIT_CHOICES,
        default=WORKLOAD_UNIT_MAN_DAYS,
    )
    sprint_duration_days = models.PositiveSmallIntegerField(
        default=14,
        validators=[MinValueValidator(1)],
    )
    capacity_mode = models.CharField(
        max_length=20,
        choices=CAPACITY_MODE_CHOICES,
        default=CAPACITY_MODE_GLOBAL,
    )
    global_capacity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
    )
    date_created = models.DateTimeField(default=timezone.now)
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="managed_projects",
    )

    class Meta:
        ordering = ["name"]

    def clean(self):
        errors = {}

        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date must be after start date."

        if self.capacity_mode == self.CAPACITY_MODE_GLOBAL and self.global_capacity is None:
            errors["global_capacity"] = "Global capacity required for this mode."

        if self.capacity_mode == self.CAPACITY_MODE_PER_USER and self.global_capacity is not None:
            errors["global_capacity"] = "Leave empty when using per-user mode."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.code_prefix:
            self.code_prefix = self.code_prefix.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})


class ProjectMember(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_MEMBER, "Member"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER,
    )
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("project", "user")
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username} -> {self.project.name} ({self.role})"
