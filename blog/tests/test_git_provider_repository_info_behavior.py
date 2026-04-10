from unittest.mock import patch

from django.test import SimpleTestCase

from blog.services.git_data_mapper import normalize_repository_info
from blog.services.git_providers_pkg.github import GitHubProvider
from blog.services.git_providers_pkg.gitlab import GitLabProvider


class GitProviderRepositoryInfoBehaviorTests(SimpleTestCase):
    def test_github_repository_info_uses_html_url_not_api_url(self):
        provider = GitHubProvider(
            repository_url="https://github.com/acme/private-repo.git",
            access_token="token",
        )
        github_payload = {
            "name": "private-repo",
            "url": "https://api.github.com/repos/acme/private-repo",
            "html_url": "https://github.com/acme/private-repo",
            "description": "private",
            "private": True,
            "updated_at": "2026-04-10T00:00:00Z",
            "clone_url": "https://github.com/acme/private-repo.git",
        }

        with patch.object(provider, "_safe_request", return_value=github_payload):
            info = provider.get_repository_info()

        self.assertEqual(info["url"], "https://github.com/acme/private-repo")
        self.assertEqual(info["visibility"], "private")
        self.assertEqual(info["clone_url_https"], "https://github.com/acme/private-repo.git")

    def test_gitlab_repository_info_uses_web_url(self):
        provider = GitLabProvider(
            repository_url="https://gitlab.com/acme/platform.git",
            access_token="token",
        )
        gitlab_payload = {
            "name": "platform",
            "web_url": "https://gitlab.com/acme/platform",
            "description": "platform repo",
            "visibility": "private",
            "http_url_to_repo": "https://gitlab.com/acme/platform.git",
            "last_activity_at": "2026-04-10T00:00:00Z",
        }

        with patch.object(provider, "_safe_request", return_value=gitlab_payload):
            info = provider.get_repository_info()

        self.assertEqual(info["url"], "https://gitlab.com/acme/platform")
        self.assertEqual(info["clone_url_https"], "https://gitlab.com/acme/platform.git")

    def test_normalize_repository_info_fallback_keeps_browser_url(self):
        info = normalize_repository_info(
            data={},
            provider_type="github",
            repository_url="https://github.com/acme/repo.git",
        )

        self.assertEqual(info["url"], "https://github.com/acme/repo")
        self.assertEqual(info["clone_url_https"], "https://github.com/acme/repo.git")
