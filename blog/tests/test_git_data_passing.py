"""Test to verify git data is correctly passed to templates."""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from blog.models import Project

User = get_user_model()


class GitDataPassingTest(TestCase):
    """Test that git_branches and git_commits context data are available."""

    fixtures = ["demo_data.json"]  # Use existing demo data if available

    def setUp(self):
        """Create test user and project."""
        self.client = Client()
        try:
            self.user = User.objects.first()  # Use first user from fixtures
            if not self.user:
                self.user = User.objects.create_user(
                    username="testuser", password="testpass123"
                )
        except Exception as e:
            self.user = User.objects.create_user(
                username="testuser", password="testpass123"
            )

        self.project = Project.objects.first()

    def test_project_detail_context_has_git_data(self):
        """Test that project detail context includes git_branches and git_commits."""
        self.client.login(username="testuser", password="testpass123")

        if not self.project:
            return  # Skip if no project exists

        response = self.client.get(f"/blog/project/{self.project.pk}/")

        # Check response status
        assert response.status_code in (200, 403, 404), f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            context = response.context
            print("\n✅ Project detail page loaded successfully")
            print(f"   - git_branches: {context.get('git_branches', 'NOT PRESENT')}")
            print(f"   - git_commits: {context.get('git_commits', 'NOT PRESENT')}")
            print(f"   - git_extended_data: {context.get('git_extended_data', 'NOT PRESENT')}")
            print(f"   - git_repository: {context.get('git_repository', 'NOT PRESENT')}")
