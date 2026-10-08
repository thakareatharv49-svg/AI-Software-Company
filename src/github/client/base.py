from abc import ABC, abstractmethod

from src.github.models.contracts import (
    GitHubActionResult,
    GitHubBranch,
    GitHubCheckRun,
    GitHubFile,
    GitHubIssue,
    GitHubPullRequest,
    GitHubRepository,
)


class GitHubClient(ABC):
    @abstractmethod
    async def get_repository(self, owner: str, name: str) -> GitHubRepository:
        raise NotImplementedError

    @abstractmethod
    async def create_repository(
        self,
        owner: str,
        name: str,
        description: str = "",
        private: bool = False,
    ) -> GitHubRepository:
        raise NotImplementedError

    @abstractmethod
    async def create_issue(self, repository: GitHubRepository, issue: GitHubIssue) -> GitHubActionResult:
        raise NotImplementedError

    @abstractmethod
    async def create_pull_request(self, repository: GitHubRepository, pull_request: GitHubPullRequest) -> GitHubActionResult:
        raise NotImplementedError

    @abstractmethod
    async def get_branch(self, repository: GitHubRepository, branch: str) -> GitHubBranch:
        raise NotImplementedError

    @abstractmethod
    async def create_branch(self, repository: GitHubRepository, branch: str, source_sha: str) -> GitHubActionResult:
        raise NotImplementedError

    @abstractmethod
    async def get_file(self, repository: GitHubRepository, path: str, branch: str | None = None) -> GitHubFile:
        raise NotImplementedError

    @abstractmethod
    async def write_file(
        self,
        repository: GitHubRepository,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> GitHubActionResult:
        raise NotImplementedError

    @abstractmethod
    async def create_tree(
        self,
        repository: GitHubRepository,
        base_tree_sha: str,
        entries: list[dict[str, str]],
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def create_commit(
        self,
        repository: GitHubRepository,
        message: str,
        tree_sha: str,
        parent_sha: str,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def update_branch_ref(
        self,
        repository: GitHubRepository,
        branch: str,
        commit_sha: str,
        expected_sha: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_check_runs(self, repository: GitHubRepository, ref: str) -> list[GitHubCheckRun]:
        raise NotImplementedError
