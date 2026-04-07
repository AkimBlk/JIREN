"""Git provider implementations - abstracted for each hosting platform."""
from .base import GitProviderBase
from .gitea import GiteaProvider
from .github import GitHubProvider
from .gitlab import GitLabProvider
from .local import LocalGitProvider

__all__ = [
    "GitProviderBase",
    "GitHubProvider",
    "GitLabProvider",
    "GiteaProvider",
    "LocalGitProvider",
]

# Provider factory mapping
PROVIDER_MAP = {
    "github": GitHubProvider,
    "gitlab": GitLabProvider,
    "gitea": GiteaProvider,
    "local": LocalGitProvider,
}
