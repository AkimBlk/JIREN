from django.contrib.auth.models import User
from django.test import TransactionTestCase

from blog.management.commands.populate_demo_data import Command
from blog.models import Project, Ticket, TicketLink


class DemoDataCommandBehaviorTests(TransactionTestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="seed-manager", password="secret123")
        self.project = Project.objects.create(
            code_prefix="SEE",
            name="Seed Project",
            description="Seed data project",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=10,
            manager=self.manager,
        )
        self.command = Command()

    def _create_tickets(self, count):
        return [
            Ticket.objects.create(
                title=f"Ticket {index}",
                project=self.project,
                author=self.manager,
                issue_type=Ticket.ISSUE_TYPE_TASK,
                initial_load=1,
                remaining_load=1,
            )
            for index in range(count)
        ]

    def test_create_ticket_links_returns_empty_list_when_there_are_not_enough_tickets(self):
        tickets = self._create_tickets(5)

        links = self.command.create_ticket_links(tickets)

        self.assertEqual(links, [])
        self.assertEqual(TicketLink.objects.count(), 0)

    def test_create_ticket_links_creates_expected_relationships_and_is_idempotent(self):
        tickets = self._create_tickets(7)

        first_links = self.command.create_ticket_links(tickets)
        second_links = self.command.create_ticket_links(tickets)

        self.assertEqual(len(first_links), 4)
        self.assertEqual(second_links, [])
        self.assertEqual(TicketLink.objects.count(), 4)
        self.assertEqual(
            TicketLink.objects.filter(link_type=TicketLink.TYPE_BLOCKED_BY).count(),
            2,
        )
        self.assertEqual(
            TicketLink.objects.filter(link_type=TicketLink.TYPE_RELATES_TO).count(),
            2,
        )
