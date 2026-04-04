from django.contrib.auth.models import User
from django.db.models import Q
from django.test import TestCase
from django.urls import reverse

from blog.models import Project, Ticket, TicketLink


class TicketCreationRulesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="create-admin", password="secret123")
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.project = Project.objects.create(
            code_prefix="CRT",
            name="Projet creation",
            description="Projet pour creation de ticket",
            workload_unit=Project.WORKLOAD_UNIT_MAN_DAYS,
            sprint_duration_days=14,
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=8,
            manager=self.admin,
        )

    def test_status_forced_to_todo_and_script_stripped_from_description(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("ticket-create"),
            data={
                "issue_type": Ticket.ISSUE_TYPE_TASK,
                "title": "Ticket riche",
                "description": (
                    '<p>Texte <strong>important</strong></p>'
                    '<p><img src="data:image/png;base64,AAAA" alt="Schema"></p>'
                    '<script>alert("x")</script>'
                ),
                "project": self.project.pk,
                "status": Ticket.STATUS_DONE,
                "priority": "MEDIUM",
                "tags_input": "",
                "story_points": 0,
                "initial_load": 0,
                "remaining_load": 0,
            },
        )

        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title="Ticket riche")
        self.assertEqual(ticket.status, Ticket.STATUS_TODO)
        self.assertIn("<strong>important</strong>", ticket.description)
        self.assertIn("data:image/png;base64,AAAA", ticket.description)
        self.assertNotIn("<script", ticket.description)

        detail_response = self.client.get(reverse("ticket-detail", kwargs={"pk": ticket.pk}))
        detail_content = detail_response.content.decode("utf-8")
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn("<strong>important</strong>", detail_content)
        self.assertIn("data:image/png;base64,AAAA", detail_content)
        self.assertNotIn("alert(", detail_content)


class TicketLinkTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="link-admin", password="secret123")
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.project = Project.objects.create(
            code_prefix="LNK",
            name="Projet liens",
            description="Projet avec dependances",
            workload_unit=Project.WORKLOAD_UNIT_MAN_DAYS,
            sprint_duration_days=14,
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=8,
            manager=self.admin,
        )

        self.primary = Ticket.objects.create(
            title="Ticket principal",
            project=self.project,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_TASK,
            initial_load=3,
            remaining_load=3,
        )
        self.blocker = Ticket.objects.create(
            title="Ticket bloquant",
            project=self.project,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_TASK,
            initial_load=1,
            remaining_load=1,
        )
        self.related = Ticket.objects.create(
            title="Ticket relie",
            project=self.project,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_TASK,
            initial_load=2,
            remaining_load=2,
        )

    def test_update_persists_blocked_by_and_relates_to_links(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("ticket-update", kwargs={"pk": self.primary.pk}),
            data={
                "title": self.primary.title,
                "description": "Ticket mis a jour",
                "issue_type": Ticket.ISSUE_TYPE_TASK,
                "sprint": "",
                "epic": "",
                "assignee": "",
                "status": Ticket.STATUS_TODO,
                "priority": "MEDIUM",
                "tags_input": "",
                "blocked_by_tickets": [self.blocker.pk],
                "relates_to_tickets": [self.related.pk],
                "story_points": 0,
                "initial_load": 3,
                "remaining_load": 3,
                "color": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            TicketLink.objects.filter(
                source_ticket=self.primary,
                target_ticket=self.blocker,
                link_type=TicketLink.TYPE_BLOCKED_BY,
            ).exists()
        )
        self.assertTrue(
            TicketLink.objects.filter(link_type=TicketLink.TYPE_RELATES_TO).filter(
                Q(source_ticket=self.primary, target_ticket=self.related)
                | Q(source_ticket=self.related, target_ticket=self.primary)
            ).exists()
        )

    def test_detail_shows_links_from_both_directions(self):
        TicketLink.objects.create(
            source_ticket=self.primary,
            target_ticket=self.blocker,
            link_type=TicketLink.TYPE_BLOCKED_BY,
        )
        TicketLink.objects.create(
            source_ticket=self.primary,
            target_ticket=self.related,
            link_type=TicketLink.TYPE_RELATES_TO,
        )

        self.client.force_login(self.admin)
        primary_response = self.client.get(reverse("ticket-detail", kwargs={"pk": self.primary.pk}))
        blocker_response = self.client.get(reverse("ticket-detail", kwargs={"pk": self.blocker.pk}))
        related_response = self.client.get(reverse("ticket-detail", kwargs={"pk": self.related.pk}))

        self.assertEqual([t.pk for t in primary_response.context["blocked_by_tickets"]], [self.blocker.pk])
        self.assertEqual([t.pk for t in primary_response.context["related_tickets"]], [self.related.pk])
        self.assertContains(primary_response, self.blocker.title)
        self.assertContains(primary_response, self.related.title)

        self.assertEqual([t.pk for t in blocker_response.context["blocks_tickets"]], [self.primary.pk])
        self.assertContains(blocker_response, self.primary.title)

        self.assertEqual([t.pk for t in related_response.context["related_tickets"]], [self.primary.pk])
        self.assertContains(related_response, self.primary.title)

    def test_deleting_ticket_removes_its_links(self):
        TicketLink.objects.create(
            source_ticket=self.primary,
            target_ticket=self.blocker,
            link_type=TicketLink.TYPE_BLOCKED_BY,
        )
        TicketLink.objects.create(
            source_ticket=self.primary,
            target_ticket=self.related,
            link_type=TicketLink.TYPE_RELATES_TO,
        )
        self.primary.delete()
        self.assertEqual(TicketLink.objects.count(), 0)
