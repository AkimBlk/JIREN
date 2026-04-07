from datetime import date

from django.contrib.auth.models import User
from django.urls import reverse
from django.test import RequestFactory, TestCase

from blog.models import Project, ProjectMember, Sprint, SprintUserCapacity, Ticket
from blog.views import TicketCreateView, TicketListView
from blog.views.queries import save_sprint_user_capacities as _save_sprint_user_capacities


class TicketViewConfigurationBehaviorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.manager = User.objects.create_user(username="view-manager", password="secret123")
        self.member = User.objects.create_user(username="view-member", password="secret123")

        self.project = Project.objects.create(
            code_prefix="CFG",
            name="Configured Project",
            description="View configuration tests",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=8,
            manager=self.manager,
        )
        ProjectMember.objects.create(project=self.project, user=self.manager, role=ProjectMember.ROLE_ADMIN)
        ProjectMember.objects.create(project=self.project, user=self.member, role=ProjectMember.ROLE_MEMBER)

        self.active_sprint = Sprint.objects.create(
            project=self.project,
            name="Active Sprint",
            status=Sprint.STATUS_ACTIVE,
            capacity_mode=Sprint.CAPACITY_MODE_GLOBAL,
            capacity=5,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.manager,
        )
        self.closed_sprint = Sprint.objects.create(
            project=self.project,
            name="Closed Sprint",
            status=Sprint.STATUS_CLOSED,
            capacity_mode=Sprint.CAPACITY_MODE_GLOBAL,
            capacity=5,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
            created_by=self.manager,
            closed_at="2026-03-14T10:00:00Z",
        )
        self.epic = Ticket.objects.create(
            title="Epic",
            project=self.project,
            author=self.manager,
            issue_type=Ticket.ISSUE_TYPE_EPIC,
            color="#123456",
        )
        self.story = Ticket.objects.create(
            title="Story",
            project=self.project,
            sprint=self.active_sprint,
            author=self.manager,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            story_points=2,
            initial_load=2,
            remaining_load=2,
        )

    def test_ticket_list_view_returns_active_sprint_tickets_only(self):
        view = TicketListView()
        request = self.factory.get("/kanban/", {"project": self.project.pk})
        request.user = self.manager
        view.request = request

        queryset = view.get_queryset()

        self.assertEqual(list(queryset), [self.story])
        self.assertEqual(view.selected_tag, None)
        self.assertEqual(view.get_selected_project(), self.project)

    def test_ticket_create_view_configures_project_specific_form_querysets(self):
        request = self.factory.get("/ticket/new/", {"project": self.project.pk})
        request.user = self.manager
        view = TicketCreateView()
        view.request = request
        view.args = ()
        view.kwargs = {}

        form = view.get_form()

        self.assertNotIn("status", form.fields)
        self.assertEqual(form.fields["project"].initial, self.project.pk)
        self.assertEqual(list(form.fields["sprint"].queryset), [self.active_sprint])
        self.assertEqual(list(form.fields["epic"].queryset), [self.epic])
        self.assertIn(self.manager, form.fields["assignee"].queryset)
        self.assertIn(self.member, form.fields["assignee"].queryset)
        self.assertEqual(form.fields["color"].widget.input_type, "color")

    def test_save_sprint_user_capacities_enforces_positive_integer_rows(self):
        sprint = Sprint.objects.create(
            project=self.project,
            name="Per user sprint",
            status=Sprint.STATUS_PLANNED,
            capacity_mode=Sprint.CAPACITY_MODE_PER_USER,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 14),
            created_by=self.manager,
        )

        _save_sprint_user_capacities(
            sprint,
            {
                f"capacity_user_{self.manager.pk}": "3",
                f"capacity_user_{self.member.pk}": "2",
            },
        )

        self.assertEqual(
            list(sprint.user_capacities.values_list("capacity", flat=True)),
            [3, 2],
        )

        with self.assertRaisesMessage(Exception, "whole number"):
            _save_sprint_user_capacities(
                sprint,
                {f"capacity_user_{self.manager.pk}": "broken"},
            )

        with self.assertRaisesMessage(Exception, "greater than 0"):
            _save_sprint_user_capacities(
                sprint,
                {f"capacity_user_{self.manager.pk}": "0"},
            )

        with self.assertRaisesMessage(Exception, "at least one user capacity"):
            _save_sprint_user_capacities(sprint, {})

    def test_save_sprint_user_capacities_clears_rows_in_global_mode(self):
        sprint = Sprint.objects.create(
            project=self.project,
            name="Global sprint",
            status=Sprint.STATUS_PLANNED,
            capacity_mode=Sprint.CAPACITY_MODE_PER_USER,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            created_by=self.manager,
        )
        SprintUserCapacity.objects.create(sprint=sprint, user=self.manager, capacity=4)

        sprint.capacity_mode = Sprint.CAPACITY_MODE_GLOBAL
        _save_sprint_user_capacities(sprint, {})

        self.assertFalse(sprint.user_capacities.exists())

    def test_ticket_create_page_avoids_helper_microcopy(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("ticket-create"), data={"project": self.project.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Epic")
        self.assertContains(response, "Assignee")
        self.assertNotContains(response, "Choose an epic")
        self.assertNotContains(response, "Choose a member")
        self.assertNotContains(response, "Describe the ticket...")
        self.assertNotContains(response, "No blocking ticket selected.")
        self.assertNotContains(response, "No related ticket selected.")

    def test_all_tickets_export_returns_csv(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("all-tickets"), data={"export": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("id,type,title,status,priority,project,assignee,tags", content)
        self.assertIn("Configured Project", content)
        self.assertIn("Story", content)

    def test_ticket_card_uses_project_code_prefix_not_hardcoded_at(self):
        """
        Bug    : ticket_card.html used hardcoded "AT-" prefix instead of
                 ticket.project.code_prefix — all kanban cards showed wrong ID.
        Root   : Template literal "AT-{{ ticket.id }}" not using model field.
        """
        self.client.force_login(self.manager)

        # The home Kanban view is scoped per project/sprint — test all-tickets
        # page which also renders the code_prefix-based ticket identity.
        response = self.client.get(reverse("all-tickets"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Should contain project code prefix "CFG" (not bare "AT-")
        self.assertIn("CFG-", content)
        # The hardcoded prefix must NOT appear for this project's tickets
        self.assertNotIn("AT-1", content)
