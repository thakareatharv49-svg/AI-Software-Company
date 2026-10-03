from abc import ABC, abstractmethod

from src.github.models.contracts import (
    GitHubActionResult,
    GitHubIssue,
    GitHubPullRequest,
    GitHubRepository,
)


class GitHubClient(ABC):
    @abstractmethod
    async def get_repository(
        self,
        owner: str,
        name: str,
    ) -> GitHubRepository:
        raise NotImplementedError

    @abstractmethod
    async def create_issue(
        self,
        repository: GitHubRepository,
        issue: GitHubIssue,
    ) -> GitHubActionResult:
        raise NotImplementedError

    @abstractmethod
    async def create_pull_request(
        self,
        repository: GitHubRepository,
        pull_request: GitHubPullRequest,
    ) -> GitHubActionResult:
        raise NotImplementedError
