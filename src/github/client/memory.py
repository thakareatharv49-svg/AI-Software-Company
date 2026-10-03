from src.github.client.base import GitHubClient
from src.github.models.contracts import (
    GitHubActionResult,
    GitHubIssue,
    GitHubPullRequest,
    GitHubRepository,
)


class InMemoryGitHubClient(GitHubClient):
    def __init__(self) -> None:
        self.issues: list[GitHubIssue] = []
        self.pull_requests: list[GitHubPullRequest] = []

    async def get_repository(
        self,
        owner: str,
        name: str,
    ) -> GitHubRepository:
        return GitHubRepository(owner=owner, name=name)

    async def create_issue(
        self,
        repository: GitHubRepository,
        issue: GitHubIssue,
    ) -> GitHubActionResult:
        self.issues.append(issue)
        return GitHubActionResult(
            success=True,
            message="Issue created",
            identifier=f"issue-{len(self.issues)}",
        )

    async def create_pull_request(
        self,
        repository: GitHubRepository,
        pull_request: GitHubPullRequest,
    ) -> GitHubActionResult:
        self.pull_requests.append(pull_request)
        return GitHubActionResult(
            success=True,
            message="Pull request created",
            identifier=f"pr-{len(self.pull_requests)}",
        )
