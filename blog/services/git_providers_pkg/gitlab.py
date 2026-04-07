"""GitLab API v4 provider implementation."""
from typing import Dict, List

from ..git_data_mapper import normalize_commits, normalize_branches, base_metadata, format_stars
from .base import GitProviderBase


class GitLabProvider(GitProviderBase):
    """GitLab API v4 provider."""

    def get_repository_info(self) -> Dict:
        """Fetch repository info from GitLab API."""
        project_id = self._get_project_id()
        return self._safe_request(f"https://gitlab.com/api/v4/projects/{project_id}")

    def get_recent_commits(self, limit: int) -> List[Dict]:
        """Fetch recent commits from GitLab API."""
        project_id = self._get_project_id()
        data = self._safe_request(f"https://gitlab.com/api/v4/projects/{project_id}/repository/commits",
                                  {"per_page": limit})
        return normalize_commits(data, "gitlab", limit)

    def get_branches(self) -> List[Dict]:
        """Fetch branches from GitLab API."""
        project_id = self._get_project_id()
        data = self._safe_request(f"https://gitlab.com/api/v4/projects/{project_id}/repository/branches")
        return normalize_branches(data, "gitlab")

    def _get_project_id(self) -> str:
        """Extract project ID from URL."""
        url = self.repository_url.rstrip("/").replace(".git", "")
        parts = url.split("/")
        return f"{parts[-2]}%2F{parts[-1]}"

    def _get_request_headers(self) -> Dict:
        """GitLab API headers."""
        headers = {}
        if self.access_token:
            headers["PRIVATE-TOKEN"] = self.access_token
        return headers

    def get_extended_metadata(self) -> Dict:
        """Fetch GitLab-specific metadata: stars, pipeline, visibility."""
        project_id = self._get_project_id()
        data = self._safe_request(f"https://gitlab.com/api/v4/projects/{project_id}")
        
        if not data:
            return base_metadata("gitlab", "GitLab", "#fc6d26")

        stars = data.get("star_count", 0)
        pipeline_status = "unknown"
        pipelines = self._safe_request(f"https://gitlab.com/api/v4/projects/{project_id}/pipelines",
                                       {"per_page": 1})
        if isinstance(pipelines, list) and pipelines:
            pipeline_status = pipelines[0].get("status", "unknown")

        result = base_metadata("gitlab", "GitLab", "#fc6d26")
        result.update({
            "stars": stars,
            "stars_display": f"⭐ {format_stars(stars)}",
            "visibility": data.get("visibility", "private"),
            "pipeline_status": pipeline_status,
            "updated_at": data.get("last_activity_at"),
            "forks_count": data.get("forks_count", 0),
            "issues_count": data.get("open_issues_count", 0),
        })
        return result
