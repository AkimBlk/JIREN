"""Base class for all Git provider implementations."""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)
GIT_API_TIMEOUT_SECONDS = 10


class GitProviderBase(ABC):
    """Abstract base class for Git hosting providers."""

    def __init__(self, repository_url: str, access_token: str = None):
        """Initialize provider with repository URL and optional token."""
        self.repository_url = repository_url
        self.access_token = access_token

    @abstractmethod
    def get_repository_info(self) -> Dict:
        """Fetch repository metadata."""

    @abstractmethod
    def get_recent_commits(self, limit: int) -> List[Dict]:
        """Fetch recent commits."""

    @abstractmethod
    def get_branches(self) -> List[Dict]:
        """Fetch repository branches."""

    @abstractmethod
    def get_extended_metadata(self) -> Dict:
        """Fetch provider-specific extended metadata."""

    @abstractmethod
    def _get_request_headers(self) -> Dict:
        """Return headers for authenticated API requests."""

    def _safe_request(self, url: str, params: Dict = None) -> Dict:
        """Execute HTTP GET request with error handling."""
        try:
            response = requests.get(url, headers=self._get_request_headers(),
                                    params=params, timeout=GIT_API_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            logger.warning(f"Request failed to {url}: {str(error)}")
            return {}
