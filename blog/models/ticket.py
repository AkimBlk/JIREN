from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .project import Project
from .sprint import Sprint, SprintUserCapacity
from .tag import Tag
from .ticket_validators import (
    validate_color,
    validate_epic_hierarchy,
    validate_global_sprint_capacity,
    validate_initial_load_immutable,
    validate_load_rules,
    validate_per_user_sprint_capacity,
    validate_sprint_rules,
    validate_story_points_rules,
    validate_tags,
)

LOAD_ISSUE_TYPES = ["STORY", "BUG", "TASK"]


class Ticket(models.Model):
    STATUS_TODO = "TODO"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_DONE = "DONE"
    STATUS_CHOICES = [
        (STATUS_TODO, "To Do"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_DONE, "Done"),
    ]

    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    ]

    ISSUE_TYPE_EPIC = "EPIC"
    ISSUE_TYPE_STORY = "STORY"
    ISSUE_TYPE_BUG = "BUG"
    ISSUE_TYPE_TASK = "TASK"
    ISSUE_TYPE_CHOICES = [
        (ISSUE_TYPE_EPIC, "Epic"),
        (ISSUE_TYPE_STORY, "Story"),
        (ISSUE_TYPE_BUG, "Bug"),
        (ISSUE_TYPE_TASK, "Task"),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    date_posted = models.DateTimeField(default=timezone.now)

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tickets")
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets_created")
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets_assigned")

    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES, default=ISSUE_TYPE_STORY)
    epic = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stories",
        limit_choices_to={"issue_type": ISSUE_TYPE_EPIC},
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="MEDIUM")

    story_points = models.PositiveIntegerField(default=0, help_text="For stories and bugs only.")
    backlog_order = models.PositiveIntegerField(default=0, db_index=True)
    initial_load = models.PositiveIntegerField(default=0, help_text="Effort estimate for stories, bugs, tasks.")
    remaining_load = models.PositiveIntegerField(default=0, help_text="Remaining effort.")

    tags = models.ManyToManyField(Tag, related_name="tickets", blank=True)
    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Hex color for epic tickets.",
        validators=[RegexValidator(regex=r"^#(?:[0-9a-fA-F]{6})$", message="Valid hex: #AABBCC")],
    )

    class Meta:
        ordering = ["backlog_order", "date_posted", "id"]

    @property
    def completed_load(self):
        return max(self.initial_load - self.remaining_load, 0)

    @property
    def display_color(self):
        return self.color or "#007bff"

    def clean(self):
        errors = {}
        validate_epic_hierarchy(self.issue_type, self.epic, self.project_id, errors)
        validate_sprint_rules(self.sprint, self.issue_type, self.project_id, errors)
        if self.pk:
            validate_tags(self.tags, self.project, errors)
        validate_story_points_rules(self.issue_type, self.story_points, errors)
        validate_initial_load_immutable(self.pk, self.initial_load, Ticket, errors)
        validate_load_rules(self.issue_type, self.initial_load, self.remaining_load, errors)
        validate_color(self.issue_type, self.color, errors)
        if self.sprint and self.issue_type in [self.ISSUE_TYPE_STORY, self.ISSUE_TYPE_BUG]:
            self._validate_sprint_capacity(errors)
        if errors:
            raise ValidationError(errors)

    def _validate_sprint_capacity(self, errors):
        if self.sprint.capacity_mode == Sprint.CAPACITY_MODE_GLOBAL:
            validate_global_sprint_capacity(self.sprint, self.pk, self.story_points, Ticket, errors)
        elif self.sprint.capacity_mode == Sprint.CAPACITY_MODE_PER_USER:
            validate_per_user_sprint_capacity(
                self.sprint, self.pk, self.story_points,
                self.assignee, SprintUserCapacity, Ticket, errors,
            )

    def save(self, *args, **kwargs):
        if self.pk:
            original = Ticket.objects.filter(pk=self.pk).only("initial_load").first()
            if original:
                self.initial_load = original.initial_load

        if self.issue_type not in LOAD_ISSUE_TYPES:
            self.initial_load = 0
            self.remaining_load = 0

        if self.issue_type not in [self.ISSUE_TYPE_STORY, self.ISSUE_TYPE_BUG]:
            self.story_points = 0

        if self.issue_type != self.ISSUE_TYPE_EPIC:
            self.color = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.project.code_prefix}] {self.title}"

    def get_absolute_url(self):
        return reverse("ticket-detail", kwargs={"pk": self.pk})
