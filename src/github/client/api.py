import base64

import httpx

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


class GitHubAPIError(RuntimeError):
    pass


class GitHubAPIClient(GitHubClient):
    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://api.github.com",
        timeout: float = 30.0,
        allow_writes: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.allow_writes = allow_writes
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ai-software-company",
            },
        )

    async def __aenter__(self) -> "GitHubAPIClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: object | None = None,
        params: dict[str, str] | None = None,
    ) -> dict:
        try:
            response = await self._client.request(
                method,
                path,
                json=json,
                params=params,
            )
        except httpx.HTTPError as exc:
            raise GitHubAPIError(f"GitHub request failed: {exc}") from exc

        if response.is_error:
            try:
                payload = response.json()
                message = payload.get("message", response.text)
            except ValueError:
                message = response.text

            raise GitHubAPIError(
                f"GitHub API error {response.status_code}: {message}"
            )

        if not response.content:
            return {}

        return response.json()

    def _require_writes(self) -> None:
        if not self.allow_writes:
            raise GitHubAPIError(
                "GitHub write operation blocked: allow_writes is disabled"
            )

    async def get_repository(
        self,
        owner: str,
        name: str,
    ) -> GitHubRepository:
        data = await self._request("GET", f"/repos/{owner}/{name}")

        return GitHubRepository(
            owner=data["owner"]["login"],
            name=data["name"],
            default_branch=data.get("default_branch", "main"),
        )

    async def create_issue(
        self,
        repository: GitHubRepository,
        issue: GitHubIssue,
    ) -> GitHubActionResult:
        self._require_writes()

        data = await self._request(
            "POST",
            f"/repos/{repository.owner}/{repository.name}/issues",
            json={
                "title": issue.title,
                "body": issue.body,
                "labels": issue.labels,
            },
        )

        return GitHubActionResult(
            success=True,
            message="Issue created",
            identifier=str(data["number"]),
        )

    async def create_pull_request(
        self,
        repository: GitHubRepository,
        pull_request: GitHubPullRequest,
    ) -> GitHubActionResult:
        self._require_writes()

        data = await self._request(
            "POST",
            f"/repos/{repository.owner}/{repository.name}/pulls",
            json={
                "title": pull_request.title,
                "head": pull_request.head,
                "base": pull_request.base,
                "body": pull_request.body,
            },
        )

        return GitHubActionResult(
            success=True,
            message="Pull request created",
            identifier=str(data["number"]),
        )

    async def get_branch(
        self,
        repository: GitHubRepository,
        branch: str,
    ) -> GitHubBranch:
        data = await self._request(
            "GET",
            f"/repos/{repository.owner}/{repository.name}/branches/{branch}",
        )

        return GitHubBranch(
            name=data["name"],
            sha=data["commit"]["sha"],
        )

    async def create_branch(
        self,
        repository: GitHubRepository,
        branch: str,
        source_sha: str,
    ) -> GitHubActionResult:
        self._require_writes()

        data = await self._request(
            "POST",
            f"/repos/{repository.owner}/{repository.name}/git/refs",
            json={
                "ref": f"refs/heads/{branch}",
                "sha": source_sha,
            },
        )

        return GitHubActionResult(
            success=True,
            message="Branch created",
            identifier=data["ref"],
        )

    async def get_file(
        self,
        repository: GitHubRepository,
        path: str,
        branch: str | None = None,
    ) -> GitHubFile:
        params = {"ref": branch} if branch else None

        data = await self._request(
            "GET",
            f"/repos/{repository.owner}/{repository.name}/contents/{path}",
            params=params,
        )

        if data.get("type") != "file":
            raise GitHubAPIError(f"GitHub path is not a file: {path}")

        encoded = data.get("content", "").replace("\n", "")
        try:
            content = base64.b64decode(encoded).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise GitHubAPIError(
                f"Unable to decode GitHub file: {path}"
            ) from exc

        return GitHubFile(
            path=data["path"],
            content=content,
            sha=data["sha"],
        )

    async def write_file(
        self,
        repository: GitHubRepository,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> GitHubActionResult:
        self._require_writes()

        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

        payload: dict[str, str] = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }

        if sha is not None:
            payload["sha"] = sha

        data = await self._request(
            "PUT",
            f"/repos/{repository.owner}/{repository.name}/contents/{path}",
            json=payload,
        )

        return GitHubActionResult(
            success=True,
            message="File written",
            identifier=data.get("commit", {}).get("sha"),
        )

    async def get_check_runs(
        self,
        repository: GitHubRepository,
        ref: str,
    ) -> list[GitHubCheckRun]:
        data = await self._request(
            "GET",
            f"/repos/{repository.owner}/{repository.name}/commits/{ref}/check-runs",
        )

        return [
            GitHubCheckRun(
                name=check["name"],
                status=check["status"],
                conclusion=check.get("conclusion"),
            )
            for check in data.get("check_runs", [])
        ]
