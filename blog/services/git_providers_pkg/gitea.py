"""Gitea API provider implementation."""
from typing import Dict, List

from ..git_data_mapper import normalize_commits, normalize_branches, base_metadata, format_stars
from .base import GitProviderBase


class GiteaProvider(GitProviderBase):
    """Gitea API provider."""

    def get_repository_info(self) -> Dict:
        """Fetch repository info from Gitea API."""
        api_url = self._get_api_url()
        return self._safe_request(api_url)

    def get_recent_commits(self, limit: int) -> List[Dict]:
        """Fetch recent commits from Gitea API."""
        api_url = self._get_api_url()
        data = self._safe_request(f"{api_url}/commits", {"limit": limit})
        return normalize_commits(data, "gitea", limit)

    def get_branches(self) -> List[Dict]:
        """Fetch branches from Gitea API."""
        api_url = self._get_api_url()
        data = self._safe_request(f"{api_url}/branches")
        return normalize_branches(data, "gitea")

    def _get_api_url(self) -> str:
        """Convert repo URL to Gitea API URL."""
        return self.repository_url.rstrip("/").replace("/", "/api/v1/repos/", 1)

    def _get_request_headers(self) -> Dict:
        """Gitea API headers."""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"token {self.access_token}"
        return headers

    def get_extended_metadata(self) -> Dict:
        """Fetch Gitea-specific metadata: stars, server version."""
        api_url = self._get_api_url()
        data = self._safe_request(api_url)
        
        if not data:
            return base_metadata("gitea", "Gitea", "#609926")

        stars = data.get("stars_count", 0)
        version_url = self.repository_url.split("/api")[0] + "/api/v1/version"
        version_data = self._safe_request(version_url)
        server_version = version_data.get("version", "unknown") if version_data else "unknown"

        result = base_metadata("gitea", "Gitea", "#609926")
        result.update({
            "stars": stars,
            "stars_display": f"⭐ {format_stars(stars)}",
            "version": server_version,
            "updated_at": data.get("updated_at"),
            "forks_count": data.get("forks_count", 0),
            "open_issues_count": data.get("open_issues_count", 0),
        })
        return result
