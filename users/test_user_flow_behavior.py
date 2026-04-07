import uuid

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from blog.models import Project, ProjectMember
from users.models import Invitation, Profile
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

    def test_login_page_uses_dedicated_auth_shell(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="helb-auth-shell helb-auth-shell--center"', html=False)
        self.assertContains(response, "Sign In")
        self.assertNotContains(response, "Connexion")
        self.assertContains(response, 'class="helb-theme-fab"', html=False)
        self.assertNotContains(response, 'class="helb-sidebar', html=False)

    def test_register_page_uses_dedicated_auth_shell(self):
        response = self.client.get(reverse("register"), data={"token": str(self.invitation.token)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="helb-auth-shell helb-auth-shell--split"', html=False)
        self.assertContains(response, "Create Account")
        self.assertNotContains(response, "Creer un compte")
        self.assertNotContains(response, 'class="helb-sidebar', html=False)

    def test_invite_page_hides_field_helper_copy(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("invite-user"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invite User")
        self.assertNotContains(response, "150 characters or fewer.")
        self.assertNotContains(response, "Letters, digits and @/./+/-/_ only.")

    def test_authenticated_home_uses_application_shell(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("blog-home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="helb-sidebar', html=False)
        self.assertContains(response, 'class="helb-topnav helb-topnav--app"', html=False)
        self.assertContains(response, 'class="helb-theme-fab"', html=False)

    def test_profile_preserves_contributor_role_for_non_admin_users(self):
        contributor = User.objects.create_user(username="contributor-user", password="secret123")
        contributor.profile.role = Profile.ROLE_CONTRIBUTEUR
        contributor.profile.save()

        contributor.profile.refresh_from_db()

        self.assertEqual(contributor.profile.role, Profile.ROLE_CONTRIBUTEUR)

    def test_profile_page_uses_editorial_profile_layout(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="atelier-profile-layout"', html=False)
        self.assertContains(response, 'class="atelier-profile-identity"', html=False)

    def test_admin_profile_embeds_role_governance_section(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage User Roles")
        self.assertContains(response, "Invite User")

    def test_manage_roles_page_uses_curated_admin_table(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("manage-roles"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="atelier-role-table-shell"', html=False)
        self.assertContains(response, 'class="atelier-stats-grid atelier-stats-grid--compact"', html=False)

    # ---- Non-regression: ROLE_CONTRIBUTEUR renamed to ROLE_CONTRIBUTOR ----

    def test_profile_role_constant_is_english_contributor(self):
        """
        Bug    : ROLE_CONTRIBUTEUR = "contributeur" stored French value in DB.
        Root   : Internal role key named/stored in French, violating English-only rule.
        Fix    : Renamed to ROLE_CONTRIBUTOR = "contributor" with data migration.
        """
        self.assertFalse(
            hasattr(Profile, 'ROLE_CONTRIBUTEUR') and Profile.ROLE_CONTRIBUTEUR == 'contributeur',
            "DB role value must be 'contributor', not 'contributeur'",
        )
        self.assertEqual(Profile.ROLE_CONTRIBUTOR, 'contributor')

    def test_contributor_profile_is_persisted_with_english_key(self):
        user = User.objects.create_user(username='contrib-test', password='x')
        user.profile.role = Profile.ROLE_CONTRIBUTOR
        user.profile.save()
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.role, 'contributor')
