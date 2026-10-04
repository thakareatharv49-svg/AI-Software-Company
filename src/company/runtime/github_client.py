from __future__ import annotations

import asyncio
import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass


class GitHubError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str
    default_branch: str
    url: str


@dataclass(frozen=True)
class GitHubPullRequest:
    number: int
    title: str
    url: str
    state: str


class GitHubClient:
    def __init__(self, runner=None) -> None:
        self._runner = runner or self._run

    @staticmethod
    def _run(command: Sequence[str]) -> str:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise GitHubError(result.stderr.strip() or "GitHub command failed")
        return result.stdout.strip()

    def auth_status(self) -> bool:
        try:
            self._runner(["gh", "auth", "status"])
            return True
        except GitHubError:
            return False

    def repository(self, owner: str, name: str) -> GitHubRepository:
        raw = self._runner(
            [
                "gh",
                "api",
                f"repos/{owner}/{name}",
                "--jq",
                "{owner:.owner.login,name:.name,default_branch:.default_branch,html_url:.html_url}",
            ]
        )
        data = json.loads(raw)
        return GitHubRepository(
            owner=data["owner"],
            name=data["name"],
            default_branch=data["default_branch"],
            url=data["html_url"],
        )

    def create_branch(
        self,
        owner: str,
        name: str,
        branch: str,
        base: str,
    ) -> None:
        ref = self._runner(
            [
                "gh",
                "api",
                f"repos/{owner}/{name}/git/ref/heads/{base}",
                "--jq",
                ".object.sha",
            ]
        )
        self._runner(
            [
                "gh",
                "api",
                f"repos/{owner}/{name}/git/refs",
                "-f",
                f"ref=refs/heads/{branch}",
                "-f",
                f"sha={ref}",
            ]
        )

    def create_pull_request(
        self,
        owner: str,
        name: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> GitHubPullRequest:
        raw = self._runner(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                f"{owner}/{name}",
                "--title",
                title,
                "--body",
                body,
                "--head",
                head,
                "--base",
                base,
                "--json",
                "number,title,url,state",
            ]
        )
        data = json.loads(raw)
        return GitHubPullRequest(
            number=int(data["number"]),
            title=data["title"],
            url=data["url"],
            state=data["state"],
        )

    def merge_pull_request(
        self,
        owner: str,
        name: str,
        number: int,
        method: str = "squash",
    ) -> None:
        self._runner(
            [
                "gh",
                "pr",
                "merge",
                str(number),
                "--repo",
                f"{owner}/{name}",
                f"--{method}",
                "--delete-branch",
            ]
        )

    async def acreate_pull_request(
        self,
        owner: str,
        name: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> GitHubPullRequest:
        return await asyncio.to_thread(
            self.create_pull_request,
            owner,
            name,
            title,
            body,
            head,
            base,
        )
