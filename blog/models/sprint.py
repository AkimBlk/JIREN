from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .project import Project, ProjectMember


class Sprint(models.Model):
    STATUS_PLANNED = "PLANNED"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_CLOSED = "CLOSED"
    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planned"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
    ]

    CAPACITY_MODE_GLOBAL = "GLOBAL"
    CAPACITY_MODE_PER_USER = "PER_USER"
    CAPACITY_MODE_CHOICES = [
        (CAPACITY_MODE_GLOBAL, "Global capacity"),
        (CAPACITY_MODE_PER_USER, "Capacity per user"),
    ]

    TEMPLATE_CLASSIC = "ticket_card"
    TEMPLATE_ACCENT = "ticket_card_alt"
    TEMPLATE_COMPACT = "ticket_card_compact"
    TICKET_TEMPLATE_CHOICES = [
        (TEMPLATE_CLASSIC, "Template 1 - Classic"),
        (TEMPLATE_ACCENT, "Template 2 - Accent"),
        (TEMPLATE_COMPACT, "Template 3 - Compact"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="sprints",
    )
    name = models.CharField(max_length=120)
    objective = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
    )
    capacity_mode = models.CharField(
        max_length=20,
        choices=CAPACITY_MODE_CHOICES,
        default=CAPACITY_MODE_GLOBAL,
    )
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Global sprint capacity in story points.",
    )
    ticket_template = models.CharField(
        max_length=30,
        choices=TICKET_TEMPLATE_CHOICES,
        default=TEMPLATE_CLASSIC,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sprints",
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["project", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(status="ACTIVE"),
                name="uniq_active_sprint_per_project",
            )
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    def clean(self):
        errors = {}

        if self.end_date and self.start_date and self.end_date < self.start_date:
            errors["end_date"] = "Sprint end date must be after start date."

        if self.status == self.STATUS_ACTIVE:
            another_active = Sprint.objects.filter(
                project=self.project, status=self.STATUS_ACTIVE
            ).exclude(pk=self.pk)
            if another_active.exists():
                errors["status"] = "Only one active sprint per project."

        if self.status == self.STATUS_CLOSED and not self.closed_at:
            errors["status"] = "Closed sprint must be closed via action."

        if self.capacity_mode == self.CAPACITY_MODE_GLOBAL and not self.capacity:
            errors["capacity"] = "Global capacity required in global mode."

        if self.capacity_mode == self.CAPACITY_MODE_PER_USER and self.capacity:
            errors["capacity"] = "Leave empty when using per-user mode."

        if errors:
            raise ValidationError(errors)

    def delete(self, *args, **kwargs):
        if self.status == self.STATUS_ACTIVE:
            raise ValidationError("Active sprint cannot be deleted.")
        super().delete(*args, **kwargs)

    def start(self):
        if self.status != self.STATUS_PLANNED:
            raise ValidationError("Only planned sprints can be started.")

        another = Sprint.objects.filter(
            project=self.project, status=self.STATUS_ACTIVE
        ).exclude(pk=self.pk)
        if another.exists():
            raise ValidationError("Only one active sprint per project.")

        self.status = self.STATUS_ACTIVE
        self.activated_at = timezone.now()
        self.save(update_fields=["status", "activated_at"])

    def close(self):
        if self.status != self.STATUS_ACTIVE:
            raise ValidationError("Only active sprints can be closed.")

        with transaction.atomic():
            from .ticket import Ticket
            self.tickets.exclude(status=Ticket.STATUS_DONE).update(sprint=None)
            self.status = self.STATUS_CLOSED
            self.closed_at = timezone.now()
            self.save(update_fields=["status", "closed_at"])

    def ticket_count(self):
        return self.tickets.count()

    def total_story_points(self):
        from .ticket import Ticket
        return (
            self.tickets.filter(
                issue_type__in=[Ticket.ISSUE_TYPE_STORY, Ticket.ISSUE_TYPE_BUG]
            ).aggregate(total=Sum("story_points")).get("total") or 0
        )

    def configured_capacity(self):
        if self.capacity_mode == self.CAPACITY_MODE_GLOBAL:
            return self.capacity or 0
        return self.user_capacities.aggregate(total=Sum("capacity")).get("total") or 0

    def remaining_capacity(self):
        return max(self.configured_capacity() - self.total_story_points(), 0)

    def is_full(self):
        configured = self.configured_capacity()
        return configured > 0 and self.total_story_points() >= configured


class SprintUserCapacity(models.Model):
    sprint = models.ForeignKey(
        Sprint,
        on_delete=models.CASCADE,
        related_name="user_capacities",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sprint_capacities",
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Story point capacity for this user in sprint.",
    )

    class Meta:
        unique_together = ("sprint", "user")
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.sprint.name} - {self.user.username}: {self.capacity} SP"

    def clean(self):
        is_member = (
            self.sprint.project.manager_id == self.user_id
            or ProjectMember.objects.filter(
                project=self.sprint.project, user=self.user
            ).exists()
        )
        if not is_member:
            raise ValidationError({"user": "User not a member of sprint's project."})
