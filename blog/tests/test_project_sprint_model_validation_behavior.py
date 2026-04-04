from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from blog.models import Project, Sprint


class ProjectValidationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager-pv", password="secret123")

    def test_rejects_end_date_before_start_date(self):
        project = Project(
            code_prefix="BAD",
            name="Broken project",
            description="Broken",
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 1),
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=5,
            manager=self.manager,
        )
        with self.assertRaises(ValidationError) as ctx:
            project.full_clean()
        self.assertIn("end_date", ctx.exception.message_dict)

    def test_rejects_per_user_mode_with_global_capacity_set(self):
        project = Project(
            code_prefix="BAD2",
            name="Broken capacity",
            description="Broken",
            capacity_mode=Project.CAPACITY_MODE_PER_USER,
            global_capacity=3,
            manager=self.manager,
        )
        with self.assertRaises(ValidationError) as ctx:
            project.full_clean()
        self.assertIn("global_capacity", ctx.exception.message_dict)


class SprintValidationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager-sv", password="secret123")
        self.project = Project.objects.create(
            code_prefix="SPV",
            name="Sprint Validation Project",
            description="Test",
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=12,
            manager=self.manager,
        )
        Sprint.objects.create(
            project=self.project,
            name="Active Sprint",
            status=Sprint.STATUS_ACTIVE,
            capacity_mode=Sprint.CAPACITY_MODE_GLOBAL,
            capacity=5,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 14),
            created_by=self.manager,
        )

    def test_rejects_second_active_sprint_per_project(self):
        sprint = Sprint(
            project=self.project,
            name="Conflicting sprint",
            status=Sprint.STATUS_ACTIVE,
            capacity_mode=Sprint.CAPACITY_MODE_GLOBAL,
            capacity=4,
            start_date=date(2026, 4, 15),
            end_date=date(2026, 4, 28),
            created_by=self.manager,
        )
        with self.assertRaises(ValidationError) as ctx:
            sprint.full_clean()
        self.assertIn("status", ctx.exception.message_dict)

    def test_rejects_per_user_mode_with_capacity_set(self):
        sprint = Sprint(
            project=self.project,
            name="Bad capacity sprint",
            status=Sprint.STATUS_PLANNED,
            capacity_mode=Sprint.CAPACITY_MODE_PER_USER,
            capacity=4,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 14),
            created_by=self.manager,
        )
        with self.assertRaises(ValidationError) as ctx:
            sprint.full_clean()
        self.assertIn("capacity", ctx.exception.message_dict)
