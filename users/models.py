import uuid

from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from PIL import Image

username_validator = UnicodeUsernameValidator()


class Profile(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"
    ROLE_CONTRIBUTEUR = "contributeur"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_CONTRIBUTEUR, "Contributor"),
        (ROLE_MEMBER, "Member"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default="default.jpg", upload_to="profile_pics")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)

    def __str__(self):
        return f"{self.user.username} Profile ({self.role})"

    def is_admin(self):
        return self.user.is_superuser or self.user.is_staff

    def can_contribute(self):
        return self.user.is_authenticated

    def save(self, *args, **kwargs):
        if self.user.is_superuser or self.user.is_staff:
            self.role = self.ROLE_ADMIN
        else:
            self.role = self.ROLE_MEMBER

        super().save(*args, **kwargs)

        img = Image.open(self.image.path)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        if img.height > 300 or img.width > 300:
            img.thumbnail((300, 300))
            img.save(self.image.path)


class Invitation(models.Model):
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [
        (ROLE_MEMBER, "Project member"),
    ]

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField()
    username = models.CharField(
        max_length=150,
        validators=[username_validator],
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invitations_sent",
    )
    created_at = models.DateTimeField(default=timezone.now)
    used = models.BooleanField(default=False)
    role_assigned = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER,
    )
    project = models.ForeignKey(
        "blog.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invitations",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["username"],
                condition=models.Q(used=False),
                name="unique_pending_invitation_username",
            ),
        ]

    def clean(self):
        super().clean()

        if self.used or not self.username:
            return

        if User.objects.filter(username=self.username).exists():
            raise ValidationError({"username": "A user with that username already exists."})

        reserved_usernames = Invitation.objects.filter(username=self.username, used=False)
        if self.pk:
            reserved_usernames = reserved_usernames.exclude(pk=self.pk)

        if reserved_usernames.exists():
            raise ValidationError({"username": "This username is already reserved by a pending invitation."})

    def __str__(self):
        return f"Invite -> {self.username} ({self.email}) as {self.get_role_assigned_display()} (used={self.used})"

    def is_valid(self):
        return not self.used
