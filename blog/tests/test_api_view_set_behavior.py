from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from blog.api_views import TagViewSet, TicketTagViewSet
from blog.models import Project, ProjectMember, Tag, Ticket


class TagApiViewSetBehaviorTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.manager = User.objects.create_user(username="api-manager", password="secret123")
        self.member = User.objects.create_user(username="api-member", password="secret123")
        self.staff = User.objects.create_user(username="api-staff", password="secret123")
        self.staff.is_staff = True
        self.staff.save(update_fields=["is_staff"])
        self.outsider = User.objects.create_user(username="api-outsider", password="secret123")

        self.project = Project.objects.create(
            code_prefix="API",
            name="API Project",
            description="API tests",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=10,
            manager=self.manager,
        )
        ProjectMember.objects.create(project=self.project, user=self.member, role=ProjectMember.ROLE_MEMBER)
        self.tag = Tag.objects.create(project=self.project, name="Backend")

    def test_tag_create_uses_project_scope_and_rejects_outsiders(self):
        create_view = TagViewSet.as_view({"post": "create"})

        allowed_request = self.factory.post("/api/projects/tags/", {"name": "Frontend"}, format="json")
        force_authenticate(allowed_request, user=self.member)
        allowed_response = create_view(allowed_request, project_id=self.project.pk)
        self.assertEqual(allowed_response.status_code, 201)
        self.assertEqual(allowed_response.data["project"], self.project.pk)

        denied_request = self.factory.post("/api/projects/tags/", {"name": "Security"}, format="json")
        force_authenticate(denied_request, user=self.outsider)
        denied_response = create_view(denied_request, project_id=self.project.pk)
        self.assertEqual(denied_response.status_code, 403)

    def test_tag_destroy_is_reserved_for_project_managers_or_staff(self):
        destroy_view = TagViewSet.as_view({"delete": "destroy"})

        member_request = self.factory.delete("/api/projects/tags/1/")
        force_authenticate(member_request, user=self.member)
        member_response = destroy_view(member_request, project_id=self.project.pk, pk=self.tag.pk)
        self.assertEqual(member_response.status_code, 403)

        staff_request = self.factory.delete("/api/projects/tags/1/")
        force_authenticate(staff_request, user=self.staff)
        staff_response = destroy_view(staff_request, project_id=self.project.pk, pk=self.tag.pk)
        self.assertEqual(staff_response.status_code, 204)


class TicketTagApiViewSetBehaviorTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.manager = User.objects.create_user(username="ticket-manager", password="secret123")
        self.member = User.objects.create_user(username="ticket-member", password="secret123")
        self.outsider = User.objects.create_user(username="ticket-outsider", password="secret123")

        self.project = Project.objects.create(
            code_prefix="TAG",
            name="Tag Project",
            description="Ticket tag tests",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=8,
            manager=self.manager,
        )
        ProjectMember.objects.create(project=self.project, user=self.member, role=ProjectMember.ROLE_MEMBER)
        self.ticket = Ticket.objects.create(
            title="Ticket with tags",
            project=self.project,
            author=self.manager,
            issue_type=Ticket.ISSUE_TYPE_TASK,
            initial_load=1,
            remaining_load=1,
        )
        self.tag = Tag.objects.create(project=self.project, name="Frontend")

    def test_add_tag_supports_identifier_or_name_and_keeps_existing_assignments(self):
        add_view = TicketTagViewSet.as_view({"post": "add_tag"})

        id_request = self.factory.post("/api/tickets/tags/add/", {"tag_id": self.tag.pk}, format="json")
        force_authenticate(id_request, user=self.member)
        id_response = add_view(id_request, ticket_id=self.ticket.pk)
        self.assertEqual(id_response.status_code, 200)
        self.assertEqual(len(id_response.data["tags"]), 1)

        name_request = self.factory.post(
            "/api/tickets/tags/add/",
            {"tag_name": self.tag.name.lower()},
            format="json",
        )
        force_authenticate(name_request, user=self.member)
        name_response = add_view(name_request, ticket_id=self.ticket.pk)
        self.assertEqual(name_response.status_code, 200)
        self.assertIn("already", name_response.data["detail"])

    def test_remove_tag_reports_missing_assignments_and_denies_outsiders(self):
        remove_view = TicketTagViewSet.as_view({"post": "remove_tag"})

        outsider_request = self.factory.post("/api/tickets/tags/remove/", {"tag_id": self.tag.pk}, format="json")
        force_authenticate(outsider_request, user=self.outsider)
        outsider_response = remove_view(outsider_request, ticket_id=self.ticket.pk)
        self.assertEqual(outsider_response.status_code, 404)

        member_request = self.factory.post("/api/tickets/tags/remove/", {"tag_id": self.tag.pk}, format="json")
        force_authenticate(member_request, user=self.member)
        member_response = remove_view(member_request, ticket_id=self.ticket.pk)
        self.assertEqual(member_response.status_code, 400)

        self.ticket.tags.add(self.tag)
        second_request = self.factory.post("/api/tickets/tags/remove/", {"tag_name": self.tag.name}, format="json")
        force_authenticate(second_request, user=self.member)
        second_response = remove_view(second_request, ticket_id=self.ticket.pk)
        self.assertEqual(second_response.status_code, 200)
        self.assertFalse(self.ticket.tags.filter(pk=self.tag.pk).exists())
