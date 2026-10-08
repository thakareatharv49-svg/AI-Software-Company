from src.github.client.base import GitHubClient
from src.github.models.contracts import (
    GitHubActionResult,
    GitHubBranch,
    GitHubCheckRun,
    GitHubFile,
    GitHubIssue,
    GitHubPullRequest,
    GitHubRepository,
)


class InMemoryGitHubClient(GitHubClient):
    def __init__(self) -> None:
        self.issues: list[GitHubIssue] = []
        self.pull_requests: list[GitHubPullRequest] = []
        self.branches: dict[str, GitHubBranch] = {}
        self.files: dict[str, GitHubFile] = {}
        self.check_runs: dict[str, list[GitHubCheckRun]] = {}

    async def get_repository(
        self,
        owner: str,
        name: str,
    ) -> GitHubRepository:
        return GitHubRepository(owner=owner, name=name)

    async def create_repository(
        self,
        owner: str,
        name: str,
        description: str = "",
        private: bool = False,
    ) -> GitHubRepository:
        repository = GitHubRepository(owner=owner, name=name)
        return repository

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

    async def get_branch(
        self,
        repository: GitHubRepository,
        branch: str,
    ) -> GitHubBranch:
        key = f"{repository.owner}/{repository.name}:{branch}"

        return self.branches.get(
            key,
            GitHubBranch(
                name=branch,
                sha="memory-sha",
            ),
        )

    async def create_branch(
        self,
        repository: GitHubRepository,
        branch: str,
        source_sha: str,
    ) -> GitHubActionResult:
        key = f"{repository.owner}/{repository.name}:{branch}"

        self.branches[key] = GitHubBranch(
            name=branch,
            sha=source_sha,
        )

        return GitHubActionResult(
            success=True,
            message="Branch created",
            identifier=branch,
        )

    async def get_file(
        self,
        repository: GitHubRepository,
        path: str,
        branch: str | None = None,
    ) -> GitHubFile:
        key = (
            f"{repository.owner}/{repository.name}:"
            f"{branch or repository.default_branch}:{path}"
        )

        if key not in self.files:
            raise KeyError(f"File not found: {path}")

        return self.files[key]

    async def write_file(
        self,
        repository: GitHubRepository,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> GitHubActionResult:
        key = (
            f"{repository.owner}/{repository.name}:"
            f"{branch}:{path}"
        )

        file_sha = sha or f"memory-file-{len(self.files) + 1}"

        self.files[key] = GitHubFile(
            path=path,
            content=content,
            sha=file_sha,
        )

        return GitHubActionResult(
            success=True,
            message="File written",
            identifier=file_sha,
        )

    async def create_tree(
        self,
        repository: GitHubRepository,
        base_tree_sha: str,
        entries: list[dict[str, str]],
    ) -> str:
        for entry in entries:
            if "content" in entry:
                await self.write_file(
                    repository,
                    entry["path"],
                    entry["content"],
                    "memory tree",
                    repository.default_branch,
                )
        return f"memory-tree-{len(self.files)}"

    async def create_commit(
        self,
        repository: GitHubRepository,
        message: str,
        tree_sha: str,
        parent_sha: str,
    ) -> str:
        return f"memory-commit-{len(self.files)}"

    async def update_branch_ref(
        self,
        repository: GitHubRepository,
        branch: str,
        commit_sha: str,
        expected_sha: str,
    ) -> None:
        return None

    async def get_check_runs(
        self,
        repository: GitHubRepository,
        ref: str,
    ) -> list[GitHubCheckRun]:
        key = f"{repository.owner}/{repository.name}:{ref}"

        return list(self.check_runs.get(key, []))
