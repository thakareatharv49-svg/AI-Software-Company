from src.config.settings import settings
from src.github.client.api import GitHubAPIClient, GitHubAPIError
from src.github.client.base import GitHubClient
from src.github.client.memory import InMemoryGitHubClient


def create_github_client(*, use_memory: bool = False) -> GitHubClient:
    if use_memory or settings.environment == "test":
        return InMemoryGitHubClient()

    if not settings.github_token:
        raise GitHubAPIError(
            "GitHub token is not configured. "
            "Set GITHUB_TOKEN or use the in-memory client."
        )

    return GitHubAPIClient(
        settings.github_token,
        base_url=settings.github_api_base_url,
        timeout=settings.github_timeout,
        allow_writes=settings.github_allow_writes,
    )
