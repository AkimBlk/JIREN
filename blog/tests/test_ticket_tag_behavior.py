from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from blog.models import Project, Sprint, Tag, Ticket


class TicketTagTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="tag-admin", password="secret123")
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.project = Project.objects.create(
            code_prefix="TAG",
            name="Projet tags",
            description="Projet avec tags",
            workload_unit=Project.WORKLOAD_UNIT_MAN_DAYS,
            sprint_duration_days=14,
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=8,
            manager=self.admin,
        )
        self.sprint = Sprint.objects.create(
            project=self.project,
            name="Sprint tags",
            status=Sprint.STATUS_ACTIVE,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.admin,
        )

    def _post_ticket(self, title, tags_input):
        return self.client.post(
            reverse("ticket-create"),
            data={
                "title": title,
                "description": "Ticket test",
                "project": self.project.pk,
                "issue_type": Ticket.ISSUE_TYPE_TASK,
                "status": Ticket.STATUS_TODO,
                "priority": "MEDIUM",
                "tags_input": tags_input,
                "story_points": 0,
                "initial_load": 0,
                "remaining_load": 0,
            },
        )

    def test_tags_are_case_insensitive_and_reused(self):
        self.client.force_login(self.admin)
        first_response = self._post_ticket("Ticket frontend", "frontend, urgent, Frontend")
        second_response = self._post_ticket("Ticket backend", "Urgent, backend")

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(Tag.objects.count(), 3)

        first_ticket = Ticket.objects.get(title="Ticket frontend")
        second_ticket = Ticket.objects.get(title="Ticket backend")

        self.assertQuerySetEqual(
            first_ticket.tags.order_by("name"),
            ["frontend", "urgent"],
            transform=lambda tag: tag.name.casefold(),
        )
        self.assertQuerySetEqual(
            second_ticket.tags.order_by("name"),
            ["backend", "urgent"],
            transform=lambda tag: tag.name.casefold(),
        )
        self.assertEqual(Tag.objects.filter(normalized_name="urgent").count(), 1)

    def test_all_tickets_view_filters_by_tag(self):
        frontend = Tag.objects.create(name="frontend", project=self.project)
        backend = Tag.objects.create(name="backend", project=self.project)

        ticket_frontend = Ticket.objects.create(
            title="Ticket front",
            project=self.project,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_TASK,
        )
        ticket_frontend.tags.add(frontend)

        ticket_backend = Ticket.objects.create(
            title="Ticket back",
            project=self.project,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_TASK,
        )
        ticket_backend.tags.add(backend)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("all-tickets"), data={"tag": frontend.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ticket front")
        self.assertNotContains(response, "Ticket back")
        self.assertEqual(response.context["selected_tag"], frontend)

    def test_kanban_view_filters_by_tag(self):
        frontend = Tag.objects.create(name="frontend", project=self.project)
        backend = Tag.objects.create(name="backend", project=self.project)

        ticket_frontend = Ticket.objects.create(
            title="Story front",
            project=self.project,
            sprint=self.sprint,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            story_points=1,
            status=Ticket.STATUS_TODO,
        )
        ticket_frontend.tags.add(frontend)

        ticket_backend = Ticket.objects.create(
            title="Story back",
            project=self.project,
            sprint=self.sprint,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            story_points=1,
            status=Ticket.STATUS_IN_PROGRESS,
        )
        ticket_backend.tags.add(backend)

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("kanban"), data={"project": self.project.pk, "tag": frontend.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Story front")
        self.assertNotContains(response, "Story back")
        self.assertEqual(response.context["selected_tag"], frontend)
