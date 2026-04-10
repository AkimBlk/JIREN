from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from blog.models import GitRepository, Project, ProjectMember, Sprint, Ticket


class ProjectMembershipTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="secret123")
        self.admin.is_superuser = True
        self.admin.save(update_fields=["is_superuser"])
        self.client.defaults["wsgi.url_scheme"] = "https"
        self.client.defaults["SERVER_PORT"] = "443"

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
        self.assertTrue(
            ProjectMember.objects.filter(
                project=project,
                user=self.admin,
                role=ProjectMember.ROLE_CONTRIBUTOR,
            ).exists()
        )
        self.assertTrue(
            ProjectMember.objects.filter(
                project=project,
                user=self.member,
                role=ProjectMember.ROLE_CONTRIBUTOR,
            ).exists()
        )

    def test_non_admin_sees_only_their_projects(self):
        visible_project = self._make_project("VIS", "Projet visible")
        hidden_project = self._make_project("HID", "Projet cache")

        ProjectMember.objects.create(
            project=visible_project,
            user=self.admin,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )
        ProjectMember.objects.create(
            project=visible_project,
            user=self.member,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )
        ProjectMember.objects.create(
            project=hidden_project,
            user=self.admin,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )

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

        ProjectMember.objects.create(
            project=visible_project,
            user=self.admin,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )
        ProjectMember.objects.create(
            project=visible_project,
            user=self.member,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )
        ProjectMember.objects.create(
            project=hidden_project,
            user=self.admin,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )

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
        self.assertEqual(post_response.status_code, 403)

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
        ProjectMember.objects.create(
            project=project,
            user=self.admin,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )
        ProjectMember.objects.create(project=project, user=self.member, role=ProjectMember.ROLE_CONTRIBUTOR)

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
        ProjectMember.objects.create(
            project=project,
            user=self.admin,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )
        ProjectMember.objects.create(project=project, user=self.member, role=ProjectMember.ROLE_CONTRIBUTOR)

        self.client.force_login(self.member)
        response = self.client.get(reverse("ticket-create"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("status", response.context["form"].fields)

        content = response.content.decode("utf-8")
        self.assertLess(content.index("id_issue_type"), content.index("id_title"))
        self.assertIn("Status:</strong> To Do", content)

    def test_project_cards_show_members(self):
        project = self._make_project("CARD", "Projet carte")
        ProjectMember.objects.create(
            project=project,
            user=self.admin,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )
        ProjectMember.objects.create(project=project, user=self.member, role=ProjectMember.ROLE_CONTRIBUTOR)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("blog-home"))

        self.assertContains(response, "Members:")
        self.assertContains(response, "admin")
        self.assertContains(response, "member")

    def test_contributor_can_mutate_tickets_and_sprints(self):
        project = self._make_project("ACL1", "Permission Matrix")
        contributor = User.objects.create_user(username="contributor-user", password="secret123")
        ProjectMember.objects.create(
            project=project,
            user=contributor,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )
        ticket = Ticket.objects.create(
            title="Contributor ticket",
            project=project,
            author=self.admin,
            issue_type=Ticket.ISSUE_TYPE_TASK,
            initial_load=1,
            remaining_load=1,
        )
        sprint = Sprint.objects.create(
            project=project,
            name="Startable sprint",
            status=Sprint.STATUS_PLANNED,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.admin,
        )

        self.client.force_login(contributor)
        self.assertEqual(self.client.get(reverse("ticket-create"), data={"project": project.pk}).status_code, 200)
        self.assertEqual(self.client.get(reverse("ticket-update", kwargs={"pk": ticket.pk})).status_code, 200)
        self.assertEqual(self.client.post(reverse("sprint-start", kwargs={"pk": sprint.pk})).status_code, 302)

    def test_contributor_cannot_access_project_settings_or_membership_management(self):
        project = self._make_project("ACL2", "Project Settings Gate")
        contributor = User.objects.create_user(username="contrib-user", password="secret123")
        ProjectMember.objects.create(project=project, user=contributor, role=ProjectMember.ROLE_CONTRIBUTOR)

        self.client.force_login(contributor)
        self.assertEqual(self.client.get(reverse("project-update", kwargs={"pk": project.pk})).status_code, 403)
        response = self.client.post(
            reverse("project-update", kwargs={"pk": project.pk}),
            data={
                "code_prefix": project.code_prefix,
                "name": "Blocked edit",
                "description": project.description,
                "start_date": "",
                "end_date": "",
                "members": [contributor.pk],
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_non_superuser_manager_is_limited_to_contributor_actions(self):
        manager = User.objects.create_user(username="manager-contributor", password="secret123")
        project = self._make_project("ACL3", "Manager Contributor Gate", manager=manager)
        ProjectMember.objects.create(project=project, user=manager, role=ProjectMember.ROLE_CONTRIBUTOR)

        self.client.force_login(manager)
        self.assertEqual(self.client.get(reverse("project-update", kwargs={"pk": project.pk})).status_code, 403)
        self.assertEqual(self.client.get(reverse("ticket-create"), data={"project": project.pk}).status_code, 200)

    def test_project_members_can_configure_git_repository(self):
        contributor = User.objects.create_user(username="git-contributor", password="secret123")
        role_matrix = [
            ("manager", self.admin, None),
            ("contributor", contributor, ProjectMember.ROLE_CONTRIBUTOR),
        ]

        for index, (role_name, actor, membership_role) in enumerate(role_matrix, start=1):
            project = self._make_project(f"G{index}", f"Git access {role_name}")
            if membership_role:
                ProjectMember.objects.create(project=project, user=actor, role=membership_role)

            self.client.force_login(actor)
            response = self.client.post(
                reverse("git-setup-create", kwargs={"project_pk": project.pk}),
                data={
                    "repository_url": f"https://github.com/acme/repo-{role_name}",
                    "repository_type": GitRepository.REPOSITORY_TYPE_GITHUB,
                    "is_private": "",
                    "access_token": "",
                },
                secure=True,
            )

            self.assertEqual(response.status_code, 302)
            self.assertTrue(
                GitRepository.objects.filter(
                    project=project,
                    repository_type=GitRepository.REPOSITORY_TYPE_GITHUB,
                ).exists()
            )

    def test_git_repository_setup_blocks_outsider_and_anonymous(self):
        project = self._make_project("GATE", "Git access gate")

        self.client.force_login(self.outsider)
        outsider_response = self.client.post(
            reverse("git-setup-create", kwargs={"project_pk": project.pk}),
            data={
                "repository_url": "https://github.com/acme/blocked",
                "repository_type": GitRepository.REPOSITORY_TYPE_GITHUB,
                "is_private": "",
                "access_token": "",
            },
            secure=True,
        )
        self.assertEqual(outsider_response.status_code, 403)
        self.assertFalse(GitRepository.objects.filter(project=project).exists())

        self.client.logout()
        anonymous_response = self.client.post(
            reverse("git-setup-create", kwargs={"project_pk": project.pk}),
            data={
                "repository_url": "https://github.com/acme/anonymous",
                "repository_type": GitRepository.REPOSITORY_TYPE_GITHUB,
                "is_private": "",
                "access_token": "",
            },
            secure=True,
        )
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertFalse(GitRepository.objects.filter(project=project).exists())

    def test_contributor_sees_git_configuration_cta(self):
        project = self._make_project("ROCT", "Contributor Git CTA")
        contributor = User.objects.create_user(username="contributor-git-view", password="secret123")
        ProjectMember.objects.create(
            project=project,
            user=contributor,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )

        self.client.force_login(contributor)
        response = self.client.get(reverse("project-detail", kwargs={"pk": project.pk}), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user_can_configure_git"])
        self.assertContains(response, "Configure Git Repository")

    def test_git_modal_private_toggle_uses_accessible_switch_and_token_placeholder(self):
        project = self._make_project("GUX", "Git UX")
        contributor = User.objects.create_user(username="git-ux-user", password="secret123")
        ProjectMember.objects.create(
            project=project,
            user=contributor,
            role=ProjectMember.ROLE_CONTRIBUTOR,
        )

        self.client.force_login(contributor)
        response = self.client.get(reverse("project-detail", kwargs={"pk": project.pk}), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="git-private-toggle"')
        self.assertContains(response, 'id="is-private"')
        self.assertContains(response, 'data-token-placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"')
        self.assertContains(response, 'data-token-has-placeholder="true"')

