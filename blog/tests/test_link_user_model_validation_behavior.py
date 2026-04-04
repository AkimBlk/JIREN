from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from blog.models import Project, Ticket, TicketLink
from users.models import Invitation


class TicketLinkValidationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager-lv", password="secret123")
        self.other_user = User.objects.create_user(username="other-lv", password="secret123")
        self.project = Project.objects.create(
            code_prefix="LNV",
            name="Link Validation Project",
            description="Test",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=10,
            manager=self.manager,
        )
        self.other_project = Project.objects.create(
            code_prefix="OLV",
            name="Other Link Project",
            description="Secondary",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=10,
            manager=self.other_user,
        )

    def _make_task(self, project, author):
        return Ticket.objects.create(
            title="Task",
            project=project,
            author=author,
            issue_type=Ticket.ISSUE_TYPE_TASK,
            initial_load=1,
            remaining_load=1,
        )

    def test_relates_to_direction_is_normalized_to_lower_id_first(self):
        source = self._make_task(self.project, self.manager)
        target = self._make_task(self.project, self.manager)

        link = TicketLink(
            source_ticket=target,
            target_ticket=source,
            link_type=TicketLink.TYPE_RELATES_TO,
        )
        link.full_clean()
        self.assertEqual(link.source_ticket_id, source.id)
        self.assertEqual(link.target_ticket_id, target.id)

    def test_rejects_cross_project_links(self):
        source = self._make_task(self.project, self.manager)
        foreign = self._make_task(self.other_project, self.other_user)

        invalid_link = TicketLink(
            source_ticket=source,
            target_ticket=foreign,
            link_type=TicketLink.TYPE_BLOCKED_BY,
        )
        with self.assertRaises(ValidationError):
            invalid_link.full_clean()


class InvitationValidationTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username="creator-iv", password="secret123")

    def test_rejects_username_already_taken_by_existing_user(self):
        User.objects.create_user(username="reserved-name", password="secret123")
        invitation = Invitation(
            email="new@example.com",
            username="reserved-name",
            created_by=self.creator,
        )
        with self.assertRaises(ValidationError):
            invitation.full_clean()

    def test_rejects_duplicate_pending_username(self):
        Invitation.objects.create(
            email="pending@example.com",
            username="pending-name",
            created_by=self.creator,
        )
        duplicate = Invitation(
            email="other@example.com",
            username="pending-name",
            created_by=self.creator,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class ProfileRoleSyncTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager-pr", password="secret123")

    def test_profile_role_syncs_with_staff_flag(self):
        profile = self.manager.profile
        self.manager.is_staff = True
        self.manager.save(update_fields=["is_staff"])
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.role, profile.ROLE_ADMIN)

        self.manager.is_staff = False
        self.manager.is_superuser = False
        self.manager.save(update_fields=["is_staff", "is_superuser"])
        profile.save()
        profile.refresh_from_db()
        self.assertNotEqual(profile.role, profile.ROLE_ADMIN)
