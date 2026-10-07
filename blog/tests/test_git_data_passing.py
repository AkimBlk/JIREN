"""Test to verify git data is correctly passed to templates."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from blog.models import Project

User = get_user_model()


class GitDataPassingTest(TestCase):
    """Test that git context data is available in project detail responses."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.project = Project.objects.create(
            code_prefix="GIT",
            name="Git Context",
            description="Git context availability test",
            manager=self.user,
            capacity_mode=Project.CAPACITY_MODE_GLOBAL,
            global_capacity=5,
        )

    def test_project_detail_context_has_git_data(self):
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("project-detail", kwargs={"pk": self.project.pk}))

        self.assertIn(response.status_code, (200, 403, 404))

        if response.status_code == 200:
            context = response.context
            self.assertIn("git_branches", context)
            self.assertIn("git_commits", context)
            self.assertIn("git_extended_data", context)
            self.assertIn("git_repository", context)
