"""GitHub API v3 provider implementation."""
from typing import Dict, List

from ..git_data_mapper import normalize_commits, normalize_branches, base_metadata, format_stars
from .base import GitProviderBase


class GitHubProvider(GitProviderBase):
    """GitHub API v3 provider."""

    def get_repository_info(self) -> Dict:
        """Fetch repository info from GitHub API."""
        owner, repo = self._get_owner_repo()
        data = self._safe_request(f"https://api.github.com/repos/{owner}/{repo}")
        return data if data else {}

    def get_recent_commits(self, limit: int) -> List[Dict]:
        """Fetch recent commits from GitHub API."""
        owner, repo = self._get_owner_repo()
        data = self._safe_request(f"https://api.github.com/repos/{owner}/{repo}/commits",
                                  {"per_page": limit})
        return normalize_commits(data, "github", limit)

    def get_branches(self) -> List[Dict]:
        """Fetch branches from GitHub API."""
        owner, repo = self._get_owner_repo()
        data = self._safe_request(f"https://api.github.com/repos/{owner}/{repo}/branches")
        return normalize_branches(data, "github")

    def _get_owner_repo(self) -> tuple:
        """Extract owner and repo from URL."""
        url = self.repository_url.rstrip("/").replace(".git", "")
        parts = url.split("/")
        return parts[-2], parts[-1]

    def _get_request_headers(self) -> Dict:
        """GitHub API headers."""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.access_token:
            headers["Authorization"] = f"token {self.access_token}"
        return headers

    def get_extended_metadata(self) -> Dict:
        """Fetch GitHub-specific metadata: stars, language, topics."""
        owner, repo = self._get_owner_repo()
        data = self._safe_request(f"https://api.github.com/repos/{owner}/{repo}")
        
        if not data:
            return base_metadata("github", "GitHub", "#1f6feb")

        stars = data.get("stargazers_count", 0)
        result = base_metadata("github", "GitHub", "#1f6feb")
        result.update({
            "stars": stars,
            "stars_display": f"⭐ {format_stars(stars)}",
            "language": data.get("language"),
            "topics": data.get("topics", []),
            "updated_at": data.get("pushed_at"),
            "forks": data.get("forks_count", 0),
            "watchers": data.get("watchers_count", 0),
        })
        return result
