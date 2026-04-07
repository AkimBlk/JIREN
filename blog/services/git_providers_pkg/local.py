"""Local Git provider (placeholder for GitPython integration)."""
from typing import Dict, List

from .base import GitProviderBase


class LocalGitProvider(GitProviderBase):
    """Placeholder for local Git repository support."""

    def get_repository_info(self) -> Dict:
        """Return placeholder info for local repos."""
        return {
            "name": "local-repo",
            "url": self.repository_url,
            "description": "Local repository (GitPython pending)",
            "homepage_url": "",
            "last_updated": None,
            "visibility": "private",
            "clone_url_https": self.repository_url,
        }

    def get_recent_commits(self, limit: int) -> List[Dict]:
        """Placeholder for local commits."""
        return []

    def get_branches(self) -> List[Dict]:
        """Placeholder for local branches."""
        return []

    def _get_request_headers(self) -> Dict:
        """No headers for local repos."""
        return {}

    def get_extended_metadata(self) -> Dict:
        """Return stub metadata for local repos."""
        return {
            "icon": "git",
            "provider": "Local",
            "provider_color": "#f34f46",
            "stars": None,
            "description": "Local repository (GitPython pending)",
        }
