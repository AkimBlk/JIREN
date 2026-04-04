import json
from datetime import date

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from blog.models import Project, ProjectMember, Sprint, Tag, Ticket
from blog.views import (
    api_project_tags,
    api_ticket_add_tag,
    api_ticket_remove_tag,
    delete_sprint,
    move_backlog_ticket,
    update_sprint_status,
    update_ticket_status,
)


def prepare_request_with_messages(request, user):
    middleware = SessionMiddleware(lambda _request: None)
    middleware.process_request(request)
    request.session.save()
    request.user = user
    setattr(request, "_messages", FallbackStorage(request))
    return request


class TicketAndTagHttpBehaviorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.manager = User.objects.create_user(username="manager-http", password="secret123")
        self.member = User.objects.create_user(username="member-http", password="secret123")
        self.outsider = User.objects.create_user(username="outsider-http", password="secret123")

        self.project = Project.objects.create(
            code_prefix="WEB",
            name="Web Project",
            description="Request tests",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=10,
            manager=self.manager,
        )
        ProjectMember.objects.create(project=self.project, user=self.manager, role=ProjectMember.ROLE_ADMIN)
        ProjectMember.objects.create(project=self.project, user=self.member, role=ProjectMember.ROLE_MEMBER)
        self.sprint = Sprint.objects.create(
            project=self.project,
            name="Sprint Request",
            status=Sprint.STATUS_PLANNED,
            capacity_mode=Sprint.CAPACITY_MODE_GLOBAL,
            capacity=5,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.manager,
        )
        self.ticket = Ticket.objects.create(
            title="HTTP story",
            project=self.project,
            sprint=self.sprint,
            author=self.manager,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            story_points=1,
            initial_load=2,
            remaining_load=2,
            backlog_order=1,
        )
        self.other_ticket = Ticket.objects.create(
            title="Second story",
            project=self.project,
            author=self.manager,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            story_points=1,
            initial_load=1,
            remaining_load=1,
            backlog_order=2,
        )

    def test_update_ticket_status_rejects_invalid_payload_and_invalid_transition(self):
        invalid_payload_request = prepare_request_with_messages(
            self.factory.post(
                reverse("ticket-update-status", kwargs={"pk": self.ticket.pk}),
                data="not-json",
                content_type="application/json",
            ),
            self.manager,
        )
        invalid_payload_response = update_ticket_status(invalid_payload_request, self.ticket.pk)
        self.assertEqual(invalid_payload_response.status_code, 400)

        invalid_transition_request = prepare_request_with_messages(
            self.factory.post(
                reverse("ticket-update-status", kwargs={"pk": self.ticket.pk}),
                data=json.dumps({"status": Ticket.STATUS_DONE}),
                content_type="application/json",
            ),
            self.manager,
        )
        invalid_transition_response = update_ticket_status(invalid_transition_request, self.ticket.pk)
        self.assertEqual(invalid_transition_response.status_code, 400)
        self.assertIn("allowed", json.loads(invalid_transition_response.content))

    def test_update_ticket_status_persists_valid_transition(self):
        request = prepare_request_with_messages(
            self.factory.post(
                reverse("ticket-update-status", kwargs={"pk": self.ticket.pk}),
                data=json.dumps({"status": Ticket.STATUS_IN_PROGRESS}),
                content_type="application/json",
            ),
            self.manager,
        )

        response = update_ticket_status(request, self.ticket.pk)

        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ticket.status, Ticket.STATUS_IN_PROGRESS)

    def test_update_sprint_status_starts_sprint_and_rejects_invalid_choice(self):
        valid_request = prepare_request_with_messages(
            self.factory.post(
                reverse("sprint-update-status", kwargs={"pk": self.sprint.pk}),
                data={"status": Sprint.STATUS_ACTIVE},
            ),
            self.manager,
        )

        response = update_sprint_status(valid_request, self.sprint.pk)

        self.sprint.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.sprint.status, Sprint.STATUS_ACTIVE)

        invalid_request = prepare_request_with_messages(
            self.factory.post(
                reverse("sprint-update-status", kwargs={"pk": self.sprint.pk}),
                data={"status": Sprint.STATUS_PLANNED},
            ),
            self.manager,
        )
        invalid_response = update_sprint_status(invalid_request, self.sprint.pk)
        self.assertEqual(invalid_response.status_code, 302)

    def test_project_and_ticket_tag_endpoints_enforce_access_and_return_expected_payloads(self):
        tag = Tag.objects.create(project=self.project, name="Frontend")
        self.ticket.tags.add(tag)

        denied_request = prepare_request_with_messages(
            self.factory.get(reverse("api-project-tags", kwargs={"pk": self.project.pk})),
            self.outsider,
        )
        denied_response = api_project_tags(denied_request, self.project.pk)
        self.assertEqual(denied_response.status_code, 403)

        allowed_request = prepare_request_with_messages(
            self.factory.get(reverse("api-project-tags", kwargs={"pk": self.project.pk})),
            self.member,
        )
        allowed_response = api_project_tags(allowed_request, self.project.pk)
        self.assertEqual(allowed_response.status_code, 200)
        payload = json.loads(allowed_response.content)
        self.assertEqual(payload[0]["normalized_name"], "frontend")

        add_request = prepare_request_with_messages(
            self.factory.post(
                reverse("api-ticket-add-tag", kwargs={"pk": self.ticket.pk}),
                data=json.dumps({"tag_name": "Backend"}),
                content_type="application/json",
            ),
            self.manager,
        )
        add_response = api_ticket_add_tag(add_request, self.ticket.pk)
        self.assertEqual(add_response.status_code, 200)
        self.assertTrue(self.ticket.tags.filter(name="Backend").exists())

        remove_request = prepare_request_with_messages(
            self.factory.post(
                reverse("api-ticket-remove-tag", kwargs={"pk": self.ticket.pk}),
                data=json.dumps({"tag_id": tag.pk}),
                content_type="application/json",
            ),
            self.manager,
        )
        remove_response = api_ticket_remove_tag(remove_request, self.ticket.pk)
        self.assertEqual(remove_response.status_code, 200)
        self.assertFalse(self.ticket.tags.filter(pk=tag.pk).exists())

    def test_ticket_tag_endpoints_report_invalid_input(self):
        invalid_json_request = prepare_request_with_messages(
            self.factory.post(
                reverse("api-ticket-add-tag", kwargs={"pk": self.ticket.pk}),
                data="broken",
                content_type="application/json",
            ),
            self.manager,
        )
        invalid_json_response = api_ticket_add_tag(invalid_json_request, self.ticket.pk)
        self.assertEqual(invalid_json_response.status_code, 400)

        missing_tag_request = prepare_request_with_messages(
            self.factory.post(
                reverse("api-ticket-remove-tag", kwargs={"pk": self.ticket.pk}),
                data=json.dumps({}),
                content_type="application/json",
            ),
            self.manager,
        )
        missing_tag_response = api_ticket_remove_tag(missing_tag_request, self.ticket.pk)
        self.assertEqual(missing_tag_response.status_code, 400)

    def test_move_backlog_ticket_swaps_priorities_inside_product_backlog(self):
        request = prepare_request_with_messages(
            self.factory.post(
                reverse(
                    "move-backlog-ticket",
                    kwargs={"pk": self.other_ticket.pk, "direction": "up"},
                )
            ),
            self.manager,
        )

        response = move_backlog_ticket(request, self.other_ticket.pk, "up")

        self.ticket.refresh_from_db()
        self.other_ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.backlog_order, 2)
        self.assertEqual(self.other_ticket.backlog_order, 1)

    def test_delete_sprint_keeps_active_sprints_and_deletes_planned_ones(self):
        active_sprint = Sprint.objects.create(
            project=self.project,
            name="Active to keep",
            status=Sprint.STATUS_ACTIVE,
            capacity_mode=Sprint.CAPACITY_MODE_GLOBAL,
            capacity=3,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 14),
            created_by=self.manager,
        )
        active_request = prepare_request_with_messages(
            self.factory.post(reverse("sprint-delete", kwargs={"pk": active_sprint.pk})),
            self.manager,
        )
        active_response = delete_sprint(active_request, active_sprint.pk)
        self.assertEqual(active_response.status_code, 302)
        self.assertTrue(Sprint.objects.filter(pk=active_sprint.pk).exists())

        planned_request = prepare_request_with_messages(
            self.factory.post(reverse("sprint-delete", kwargs={"pk": self.sprint.pk})),
            self.manager,
        )
        planned_response = delete_sprint(planned_request, self.sprint.pk)
        self.assertEqual(planned_response.status_code, 302)
        self.assertFalse(Sprint.objects.filter(pk=self.sprint.pk).exists())
