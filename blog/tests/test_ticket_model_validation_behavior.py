from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from blog.models import Project, ProjectMember, Sprint, SprintUserCapacity, Tag, Ticket


class TicketModelValidationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager-tv", password="secret123")
        self.member = User.objects.create_user(username="member-tv", password="secret123")
        self.other_user = User.objects.create_user(username="other-tv", password="secret123")

        self.project = Project.objects.create(
            code_prefix="TKV",
            name="Ticket Validation Project",
            description="Main project",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=12,
            manager=self.manager,
        )
        self.other_project = Project.objects.create(
            code_prefix="OTV",
            name="Other Project",
            description="Secondary project",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=10,
            manager=self.other_user,
        )
        ProjectMember.objects.create(project=self.project, user=self.member, role=ProjectMember.ROLE_MEMBER)
        self.active_sprint = Sprint.objects.create(
            project=self.project,
            name="Sprint Active",
            status=Sprint.STATUS_ACTIVE,
            capacity_mode=Sprint.CAPACITY_MODE_GLOBAL,
            capacity=5,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.manager,
        )

    def _make_ticket(self, **overrides):
        data = {
            "title": "Work item",
            "project": self.project,
            "author": self.manager,
            "issue_type": Ticket.ISSUE_TYPE_STORY,
            "story_points": 1,
            "initial_load": 2,
            "remaining_load": 2,
        }
        data.update(overrides)
        return Ticket(**data)

    def test_rejects_cross_project_epic_and_closed_sprint(self):
        foreign_epic = Ticket.objects.create(
            title="Foreign epic",
            project=self.other_project,
            author=self.other_user,
            issue_type=Ticket.ISSUE_TYPE_EPIC,
            color="#112233",
        )
        closed_sprint = Sprint.objects.create(
            project=self.project,
            name="Closed sprint",
            status=Sprint.STATUS_CLOSED,
            capacity_mode=Sprint.CAPACITY_MODE_GLOBAL,
            capacity=5,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 14),
            created_by=self.manager,
            closed_at="2026-05-14T10:00:00Z",
        )
        ticket = self._make_ticket(
            epic=foreign_epic,
            sprint=closed_sprint,
            issue_type=Ticket.ISSUE_TYPE_TASK,
        )
        with self.assertRaises(ValidationError) as ctx:
            ticket.full_clean()
        self.assertIn("epic", ctx.exception.message_dict)
        self.assertIn("sprint", ctx.exception.message_dict)

    def test_rejects_invalid_story_points_load_and_color(self):
        epic = self._make_ticket(issue_type=Ticket.ISSUE_TYPE_EPIC, story_points=2, color="#abcdef")
        story = self._make_ticket(story_points=0)
        task_bad = self._make_ticket(
            issue_type=Ticket.ISSUE_TYPE_TASK,
            story_points=1,
            initial_load=1,
            remaining_load=2,
            color="#123456",
        )
        with self.assertRaises(ValidationError):
            story.full_clean()
        with self.assertRaises(ValidationError):
            epic.full_clean()
        with self.assertRaises(ValidationError) as ctx:
            task_bad.full_clean()
        self.assertIn("story_points", ctx.exception.message_dict)
        self.assertIn("remaining_load", ctx.exception.message_dict)
        self.assertIn("color", ctx.exception.message_dict)

    def test_rejects_tags_from_other_projects(self):
        ticket = Ticket.objects.create(
            title="Tagged ticket",
            project=self.project,
            author=self.manager,
            issue_type=Ticket.ISSUE_TYPE_TASK,
            initial_load=1,
            remaining_load=1,
        )
        foreign_tag = Tag.objects.create(project=self.other_project, name="foreign")
        ticket.tags.add(foreign_tag)
        with self.assertRaises(ValidationError) as ctx:
            ticket.full_clean()
        self.assertIn("tags", ctx.exception.message_dict)

    def test_rejects_global_capacity_overflow(self):
        Ticket.objects.create(
            title="Existing story",
            project=self.project,
            sprint=self.active_sprint,
            author=self.manager,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            story_points=4,
            initial_load=2,
            remaining_load=2,
        )
        ticket = self._make_ticket(sprint=self.active_sprint, story_points=2)
        with self.assertRaises(ValidationError) as ctx:
            ticket.full_clean()
        self.assertIn("sprint", ctx.exception.message_dict)

    def test_rejects_missing_per_user_capacity_and_overflow(self):
        per_user_sprint = Sprint.objects.create(
            project=self.project,
            name="Per user sprint",
            status=Sprint.STATUS_PLANNED,
            capacity_mode=Sprint.CAPACITY_MODE_PER_USER,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            created_by=self.manager,
        )
        with self.assertRaises(ValidationError) as ctx:
            self._make_ticket(sprint=per_user_sprint).full_clean()
        self.assertIn("sprint", ctx.exception.message_dict)

        SprintUserCapacity.objects.create(sprint=per_user_sprint, user=self.member, capacity=3)
        with self.assertRaises(ValidationError) as ctx:
            self._make_ticket(sprint=per_user_sprint).full_clean()
        self.assertIn("assignee", ctx.exception.message_dict)

        Ticket.objects.create(
            title="Assigned story",
            project=self.project,
            sprint=per_user_sprint,
            author=self.manager,
            assignee=self.member,
            issue_type=Ticket.ISSUE_TYPE_STORY,
            story_points=2,
            initial_load=2,
            remaining_load=2,
        )
        with self.assertRaises(ValidationError) as ctx:
            self._make_ticket(sprint=per_user_sprint, assignee=self.member, story_points=2).full_clean()
        self.assertIn("story_points", ctx.exception.message_dict)

    def test_save_normalizes_non_load_type_fields(self):
        ticket = Ticket.objects.create(
            title="Task ticket",
            project=self.project,
            author=self.manager,
            issue_type=Ticket.ISSUE_TYPE_TASK,
            story_points=5,
            initial_load=4,
            remaining_load=4,
            color="#abcdef",
        )
        ticket.issue_type = Ticket.ISSUE_TYPE_EPIC
        ticket.initial_load = 9
        ticket.remaining_load = 3
        ticket.story_points = 8
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.initial_load, 0)
        self.assertEqual(ticket.remaining_load, 0)
        self.assertEqual(ticket.story_points, 0)
        self.assertIsNone(ticket.color)
