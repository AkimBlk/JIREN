import logging
from typing import Callable, Dict, List

from django.core.cache import cache

from .git_providers_pkg import PROVIDER_MAP, GitProviderBase

logger = logging.getLogger(__name__)

GIT_COMMIT_LIMIT = 5
GIT_CACHE_TTL_SECONDS = 300


class GitServiceError(Exception):
    """Base exception for Git service operations."""


class GitService:
    """Service for accessing Git repository information."""

    def __init__(self, git_repository):
        """Initialize with GitRepository model."""
        self.repository = git_repository
        self.provider = self._create_provider()

    def _create_provider(self) -> GitProviderBase:
        """Create appropriate provider based on repository type."""
        provider_class = PROVIDER_MAP.get(self.repository.repository_type)
        if not provider_class:
            raise GitServiceError(f"Unsupported repository type: {self.repository.repository_type}")
        return provider_class(
            repository_url=self.repository.repository_url,
            access_token=self.repository.access_token,
        )

    def _cached_call(self, cache_key: str, provider_method: Callable,
                     fallback: any = None, ttl: int = GIT_CACHE_TTL_SECONDS) -> any:
        """Generic cached API call wrapper."""
        cached = cache.get(cache_key)
        if cached:
            return cached
        try:
            result = provider_method()
            cache.set(cache_key, result, ttl)
            return result
        except Exception as error:
            logger.error(f"API call failed: {str(error)}")
            return fallback if fallback else {}

    def get_repository_info(self) -> Dict:
        """Fetch repository metadata (cached 5 minutes)."""
        return self._cached_call(
            f"git_repo_info_{self.repository.pk}",
            self.provider.get_repository_info,
            self._get_fallback_repo_info()
        )

    def get_recent_commits(self, limit: int = GIT_COMMIT_LIMIT) -> List[Dict]:
        """Fetch recent commits (cached 5 minutes)."""
        return self._cached_call(
            f"git_commits_{self.repository.pk}_{limit}",
            lambda: self.provider.get_recent_commits(limit),
            []
        )

    def get_branches(self) -> List[Dict]:
        """Fetch repository branches (cached 5 minutes)."""
        return self._cached_call(
            f"git_branches_{self.repository.pk}",
            self.provider.get_branches,
            []
        )

    def get_extended_metadata(self) -> Dict:
        """Fetch provider-specific extended metadata (cached 1 hour)."""
        return self._cached_call(
            f"git_metadata_{self.repository.pk}",
            self.provider.get_extended_metadata,
            {"icon": "git", "provider": "Unknown", "error": "API unavailable"},
            ttl=3600
        )

    def _get_fallback_repo_info(self) -> Dict:
        """Fallback info when API unavailable."""
        return {
            "name": "unknown",
            "url": self.repository.repository_url,
            "description": "Repository information unavailable",
            "homepage_url": "",
            "last_updated": None,
            "visibility": "unknown",
            "clone_url_https": self.repository.repository_url,
        }

    def validate_repository(self) -> bool:
        """Validate repository accessibility."""
        info = self.get_repository_info()
        return bool(info.get("name"))
