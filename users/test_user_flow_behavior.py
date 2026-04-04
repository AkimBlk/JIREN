import uuid

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from blog.models import Project, ProjectMember
from users.models import Invitation
from users.views import invite_user, register


def prepare_request_with_messages(request, user=None):
    middleware = SessionMiddleware(lambda _request: None)
    middleware.process_request(request)
    request.session.save()
    request.user = user or User()
    setattr(request, "_messages", FallbackStorage(request))
    return request


class UserFlowBehaviorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(username="platform-admin", password="secret123")
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.project = Project.objects.create(
            code_prefix="USR",
            name="User Project",
            description="Registration tests",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=5,
            manager=self.admin,
        )
        self.invitation = Invitation.objects.create(
            email="new-user@example.com",
            username="invited-user",
            created_by=self.admin,
            project=self.project,
        )

    def test_register_requires_a_valid_invitation_token(self):
        invalid_token_request = prepare_request_with_messages(
            self.factory.get(reverse("register"), data={"token": "not-a-uuid"})
        )

        response = register(invalid_token_request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

    def test_register_creates_user_marks_invitation_used_and_adds_project_membership(self):
        request = prepare_request_with_messages(
            self.factory.post(
                reverse("register"),
                data={
                    "token": str(self.invitation.token),
                    "email": self.invitation.email,
                    "password1": "StrongPassword123!",
                    "password2": "StrongPassword123!",
                },
            )
        )

        response = register(request)

        created_user = User.objects.get(username=self.invitation.username)
        self.invitation.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))
        self.assertTrue(self.invitation.used)
        self.assertEqual(created_user.profile.role, "member")
        self.assertTrue(
            ProjectMember.objects.filter(project=self.project, user=created_user).exists()
        )

    def test_invite_user_rejects_non_admins(self):
        outsider = User.objects.create_user(username="outsider", password="secret123")
        request = prepare_request_with_messages(
            self.factory.post(
                reverse("invite-user"),
                data={"email": "blocked@example.com", "username": "blocked-user"},
            ),
            outsider,
        )

        response = invite_user(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("blog-home"))

    def test_invite_user_creates_member_invitation_for_platform_admin(self):
        request = prepare_request_with_messages(
            self.factory.post(
                reverse("invite-user"),
                data={
                    "email": "fresh@example.com",
                    "username": "fresh-user",
                    "project": self.project.pk,
                },
            ),
            self.admin,
        )

        response = invite_user(request)

        invitation = Invitation.objects.get(username="fresh-user")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("invite-user"))
        self.assertEqual(invitation.role_assigned, Invitation.ROLE_MEMBER)
        self.assertEqual(invitation.created_by, self.admin)

    def test_register_rejects_missing_token(self):
        request = prepare_request_with_messages(self.factory.get(reverse("register")))

        response = register(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))
