from __future__ import annotations

import asyncio
import base64
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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


class GitHubHttpClient(GitHubClient):
    """Dependency-free GitHub REST client for autonomous workflows."""

    def __init__(self, token: str | None = None, api_url: str = "https://api.github.com") -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_url = api_url.rstrip("/")

    async def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        return await asyncio.to_thread(self._request_sync, method, path, payload)

    def _request_sync(self, method: str, path: str, payload: dict | None) -> dict:
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is required for GitHub operations")
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            f"{self.api_url}{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode()
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"GitHub API {exc.code}: {detail}") from exc

    async def get_repository(self, owner: str, name: str) -> GitHubRepository:
        data = await self._request("GET", f"/repos/{owner}/{name}")
        return GitHubRepository(owner=owner, name=name, default_branch=data.get("default_branch", "main"))

    async def create_issue(self, repository: GitHubRepository, issue: GitHubIssue) -> GitHubActionResult:
        data = await self._request(
            "POST", f"/repos/{repository.owner}/{repository.name}/issues", issue.model_dump()
        )
        return GitHubActionResult(True, "Issue created", str(data.get("number")))

    async def create_pull_request(
        self, repository: GitHubRepository, pull_request: GitHubPullRequest
    ) -> GitHubActionResult:
        data = await self._request(
            "POST", f"/repos/{repository.owner}/{repository.name}/pulls", pull_request.model_dump()
        )
        return GitHubActionResult(True, "Pull request created", str(data.get("number")))

    async def get_branch(self, repository: GitHubRepository, branch: str) -> GitHubBranch:
        data = await self._request(
            "GET", f"/repos/{repository.owner}/{repository.name}/branches/{branch}"
        )
        return GitHubBranch(name=data["name"], sha=data["commit"]["sha"])

    async def create_branch(
        self, repository: GitHubRepository, branch: str, source_sha: str
    ) -> GitHubActionResult:
        data = await self._request(
            "POST",
            f"/repos/{repository.owner}/{repository.name}/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": source_sha},
        )
        return GitHubActionResult(True, "Branch created", data.get("ref"))

    async def get_file(
        self, repository: GitHubRepository, path: str, branch: str | None = None
    ) -> GitHubFile:
        query = f"?ref={branch}" if branch else ""
        data = await self._request(
            "GET",
            f"/repos/{repository.owner}/{repository.name}/contents/{path}{query}",
        )
        content = base64.b64decode(data["content"]).decode()
        return GitHubFile(path=path, content=content, sha=data.get("sha"))

    async def write_file(
        self,
        repository: GitHubRepository,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> GitHubActionResult:
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        data = await self._request(
            "PUT",
            f"/repos/{repository.owner}/{repository.name}/contents/{path}",
            payload,
        )
        return GitHubActionResult(True, "File committed to GitHub", data.get("commit", {}).get("sha"))

    async def get_check_runs(
        self, repository: GitHubRepository, ref: str
    ) -> list[GitHubCheckRun]:
        data = await self._request(
            "GET",
            f"/repos/{repository.owner}/{repository.name}/commits/{ref}/check-runs",
        )
        return [
            GitHubCheckRun(
                name=item["name"],
                status=item["status"],
                conclusion=item.get("conclusion"),
            )
            for item in data.get("check_runs", [])
        ]
