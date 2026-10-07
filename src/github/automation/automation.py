from src.github.client.base import GitHubClient
from src.github.models.contracts import (
    GitHubActionResult,
    GitHubIssue,
    GitHubPullRequest,
    GitHubRepository,
)


class GitHubAutomation:
    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    async def create_project_repository(
        self,
        owner: str,
        name: str,
        description: str,
        private: bool = False,
    ) -> GitHubRepository:
        return await self.client.create_repository(
            owner,
            name,
            description=description,
            private=private,
        )

    async def open_task_issue(
        self,
        repository: GitHubRepository,
        title: str,
        description: str,
    ) -> GitHubActionResult:
        return await self.client.create_issue(
            repository,
            GitHubIssue(
                title=title,
                body=description,
                labels=["ai-company", "task"],
            ),
        )

    async def open_pull_request(
        self,
        repository: GitHubRepository,
        title: str,
        head: str,
        body: str = "",
    ) -> GitHubActionResult:
        return await self.client.create_pull_request(
            repository,
            GitHubPullRequest(
                title=title,
                head=head,
                base=repository.default_branch,
                body=body,
            ),
        )
