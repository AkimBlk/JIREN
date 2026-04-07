from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from blog.models import Project, Sprint, Ticket


class SprintAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="enzo", password="secret123")
        self.project = Project.objects.create(
            code_prefix="JRN",
            name="Jiren",
            description="Projet test",
            workload_unit=Project.WORKLOAD_UNIT_MAN_DAYS,
            sprint_duration_days=14,
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=10,
            manager=self.user,
        )
        self.sprint = Sprint.objects.create(
            project=self.project,
            name="Sprint 1",
            status=Sprint.STATUS_ACTIVE,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
            created_by=self.user,
        )

    def test_story_can_be_added_to_sprint(self):
        ticket = Ticket(
            title="Story 1",
            project=self.project,
            sprint=self.sprint,
            author=self.user,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            story_points=1,
        )
        ticket.full_clean()
        ticket.save()
        self.assertEqual(ticket.sprint, self.sprint)

    def test_bug_can_be_added_to_sprint(self):
        ticket = Ticket(
            title="Bug 1",
            project=self.project,
            sprint=self.sprint,
            author=self.user,
            issue_type=Ticket.ISSUE_TYPE_BUG,
            story_points=1,
        )
        ticket.full_clean()
        ticket.save()
        self.assertEqual(ticket.sprint, self.sprint)

    def test_epic_cannot_be_added_to_sprint(self):
        ticket = Ticket(
            title="Epic 1",
            project=self.project,
            sprint=self.sprint,
            author=self.user,
            issue_type=Ticket.ISSUE_TYPE_EPIC,
        )
        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def test_only_one_active_sprint_is_allowed(self):
        second_sprint = Sprint(
            project=self.project,
            name="Sprint 2",
            status=Sprint.STATUS_ACTIVE,
            start_date=date(2026, 3, 15),
            end_date=date(2026, 3, 28),
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            second_sprint.full_clean()

    def test_start_transition_only_works_from_planned(self):
        planned = Sprint.objects.create(
            project=self.project,
            name="Sprint planifie",
            status=Sprint.STATUS_PLANNED,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            planned.start()
        self.sprint.close()
        planned.start()
        planned.refresh_from_db()
        self.assertEqual(planned.status, Sprint.STATUS_ACTIVE)
        self.assertIsNotNone(planned.activated_at)

    def test_close_moves_non_done_tickets_back_to_backlog(self):
        todo_ticket = Ticket.objects.create(
            title="Story TODO",
            project=self.project,
            sprint=self.sprint,
            author=self.user,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            status=Ticket.STATUS_TODO,
        )
        done_ticket = Ticket.objects.create(
            title="Story DONE",
            project=self.project,
            sprint=self.sprint,
            author=self.user,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            status=Ticket.STATUS_DONE,
        )
        self.sprint.close()
        todo_ticket.refresh_from_db()
        done_ticket.refresh_from_db()
        self.sprint.refresh_from_db()
        self.assertIsNone(todo_ticket.sprint)
        self.assertEqual(done_ticket.sprint_id, self.sprint.id)
        self.assertEqual(self.sprint.status, Sprint.STATUS_CLOSED)
        self.assertIsNotNone(self.sprint.closed_at)

    def test_close_transition_only_works_from_active(self):
        planned = Sprint.objects.create(
            project=self.project,
            name="Sprint futur",
            status=Sprint.STATUS_PLANNED,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            planned.close()

    def test_closed_sprint_rejects_ticket_assignment(self):
        closed_sprint = Sprint.objects.create(
            project=self.project,
            name="Sprint clos",
            status=Sprint.STATUS_CLOSED,
            start_date=date(2026, 3, 15),
            end_date=date(2026, 3, 28),
            created_by=self.user,
        )
        ticket = Ticket(
            title="Story 2",
            project=self.project,
            sprint=closed_sprint,
            author=self.user,
            issue_type=Ticket.ISSUE_TYPE_STORY,
        )
        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def test_staff_can_create_sprint_from_simple_admin_page(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("sprint-admin", kwargs={"pk": self.project.pk}),
            data={
                "name": "Sprint admin",
                "start_date": "2026-05-01",
                "end_date": "2026-05-14",
                "capacity": 10,
                "ticket_template": Sprint.TEMPLATE_CLASSIC,
            },
        )
        self.assertEqual(response.status_code, 302)
        sprint = Sprint.objects.get(project=self.project, name="Sprint admin")
        self.assertEqual(sprint.status, Sprint.STATUS_PLANNED)

    def test_sprint_admin_creation_form_hides_status_field(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("sprint-admin", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("status", response.context["form"].fields)

    def test_staff_can_update_sprint_status_from_admin_page(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)
        planned_sprint = Sprint.objects.create(
            project=self.project,
            name="Sprint planifie admin",
            status=Sprint.STATUS_PLANNED,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 14),
            created_by=self.user,
        )
        self.sprint.close()
        response = self.client.post(
            reverse("sprint-update-status", kwargs={"pk": planned_sprint.pk}),
            data={"status": Sprint.STATUS_ACTIVE},
        )
        self.assertEqual(response.status_code, 302)
        planned_sprint.refresh_from_db()
        self.assertEqual(planned_sprint.status, Sprint.STATUS_ACTIVE)
        self.assertIsNotNone(planned_sprint.activated_at)

    def test_sprint_admin_nav_page_lists_projects(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("sprint-admin-index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sprint Admin")
        self.assertContains(response, self.project.name)
        self.assertContains(response, reverse("sprint-admin", kwargs={"pk": self.project.pk}))

    def test_sprint_pages_use_english_copy_without_helper_notes(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)

        admin_response = self.client.get(reverse("sprint-admin", kwargs={"pk": self.project.pk}))
        index_response = self.client.get(reverse("sprint-admin-index"))
        update_response = self.client.get(reverse("sprint-update", kwargs={"pk": self.sprint.pk}))

        self.assertContains(admin_response, "Sprint Administration")
        self.assertNotContains(admin_response, "Administration des sprints")
        self.assertNotContains(admin_response, "Fill only the users that should receive sprint capacity.")
        self.assertNotContains(admin_response, "Choose one ticket card template for the whole sprint.")
        self.assertContains(index_response, "Manage project sprints.")
        self.assertNotContains(update_response, "Fill only the users that should receive sprint capacity.")
