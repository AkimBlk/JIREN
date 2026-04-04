from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from blog.models import Project, ProjectMember, Sprint, Ticket


class ProjectMembershipTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="secret123")
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.member = User.objects.create_user(username="member", password="secret123")

        self.outsider = User.objects.create_user(username="outsider", password="secret123")

    def _make_project(self, code, name, manager=None):
        return Project.objects.create(
            code_prefix=code,
            name=name,
            description=name,
            workload_unit=Project.WORKLOAD_UNIT_MAN_DAYS,
            sprint_duration_days=14,
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=5,
            manager=manager or self.admin,
        )

    def test_project_create_adds_selected_members(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("project-create"),
            data={
                "code_prefix": "TEAM",
                "name": "Projet equipe",
                "description": "Projet avec membres",
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "workload_unit": Project.WORKLOAD_UNIT_MAN_DAYS,
                "sprint_duration_days": 14,
                "capacity_mode": Project.CAPACITY_MODE_GLOBAL,
                "global_capacity": 10,
                "members": [self.member.id],
            },
        )
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(code_prefix="TEAM")
        self.assertTrue(ProjectMember.objects.filter(project=project, user=self.admin, role="admin").exists())
        self.assertTrue(ProjectMember.objects.filter(project=project, user=self.member, role="member").exists())

    def test_non_admin_sees_only_their_projects(self):
        visible_project = self._make_project("VIS", "Projet visible")
        hidden_project = self._make_project("HID", "Projet cache")

        ProjectMember.objects.create(project=visible_project, user=self.admin, role="admin")
        ProjectMember.objects.create(project=visible_project, user=self.member, role="contributeur")
        ProjectMember.objects.create(project=hidden_project, user=self.admin, role="admin")

        self.client.force_login(self.member)
        response = self.client.get(reverse("blog-home"))

        self.assertContains(response, "Projet visible")
        self.assertNotContains(response, "Projet cache")
        self.assertEqual(
            self.client.get(reverse("project-detail", kwargs={"pk": hidden_project.pk})).status_code,
            404,
        )

    def test_ticket_create_only_lists_visible_projects(self):
        visible_project = self._make_project("TCK1", "Projet ticket visible")
        hidden_project = self._make_project("TCK2", "Projet ticket cache")

        ProjectMember.objects.create(project=visible_project, user=self.admin, role="admin")
        ProjectMember.objects.create(project=visible_project, user=self.member, role="contributeur")
        ProjectMember.objects.create(project=hidden_project, user=self.admin, role="admin")

        self.client.force_login(self.member)
        response = self.client.get(reverse("ticket-create"))

        project_field = response.context["form"].fields["project"]
        self.assertQuerySetEqual(
            project_field.queryset.order_by("name"),
            [visible_project],
            transform=lambda p: p,
        )

        post_response = self.client.post(
            reverse("ticket-create"),
            data={
                "title": "Ticket interdit",
                "description": "Ne doit pas passer",
                "project": hidden_project.pk,
                "issue_type": Ticket.ISSUE_TYPE_STORY,
                "status": Ticket.STATUS_TODO,
                "priority": "MEDIUM",
            },
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Select a valid choice")

    def test_ticket_create_prefills_related_data_for_project(self):
        project = self._make_project("TCK3", "Projet ticket cible")
        sprint = Sprint.objects.create(
            project=project,
            name="Sprint cible",
            status=Sprint.STATUS_PLANNED,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.admin,
        )
        epic = Ticket.objects.create(
            title="Epic cible",
            project=project,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_EPIC,
        )
        ProjectMember.objects.create(project=project, user=self.admin, role="admin")
        ProjectMember.objects.create(project=project, user=self.member, role="contributeur")

        self.client.force_login(self.member)
        response = self.client.get(f"{reverse('ticket-create')}?project={project.pk}")

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertQuerySetEqual(
            form.fields["sprint"].queryset.order_by("start_date", "id"),
            [sprint],
            transform=lambda s: s,
        )
        self.assertQuerySetEqual(
            form.fields["epic"].queryset.order_by("title"),
            [epic],
            transform=lambda e: e,
        )
        self.assertQuerySetEqual(
            form.fields["assignee"].queryset.order_by("username"),
            [self.admin, self.member],
            transform=lambda u: u,
        )

    def test_ticket_create_form_shows_type_first_and_hides_status(self):
        project = self._make_project("TCK4", "Projet ticket formulaire")
        ProjectMember.objects.create(project=project, user=self.admin, role="admin")
        ProjectMember.objects.create(project=project, user=self.member, role="contributeur")

        self.client.force_login(self.member)
        response = self.client.get(reverse("ticket-create"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("status", response.context["form"].fields)

        content = response.content.decode("utf-8")
        self.assertLess(content.index("id_issue_type"), content.index("id_title"))
        self.assertIn("Status:</strong> To Do", content)

    def test_project_cards_show_members(self):
        project = self._make_project("CARD", "Projet carte")
        ProjectMember.objects.create(project=project, user=self.admin, role="admin")
        ProjectMember.objects.create(project=project, user=self.member, role="contributeur")

        self.client.force_login(self.admin)
        response = self.client.get(reverse("blog-home"))

        self.assertContains(response, "Members:")
        self.assertContains(response, "admin")
        self.assertContains(response, "member")
