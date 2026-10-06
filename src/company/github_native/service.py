from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.github.automation.automation import GitHubAutomation
from src.github.client.http import GitHubHttpClient
from src.github.models.contracts import GitHubRepository


@dataclass(frozen=True, slots=True)
class GitOperationResult:
    success: bool
    message: str
    output: str = ""


class GitHubNativeService:
    """Repository lifecycle: clone, branch, edit, commit, push and PR."""

    def __init__(
        self,
        *,
        github: GitHubAutomation | None = None,
        git_executable: str = "git",
    ) -> None:
        self.github = github or GitHubAutomation(GitHubHttpClient())
        self.git_executable = git_executable

    async def clone(self, repository: GitHubRepository, destination: Path) -> GitOperationResult:
        destination.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/{repository.owner}/{repository.name}.git"
        return await self._git(["clone", url, str(destination)], destination.parent)

    async def create_branch(self, workspace: Path, branch: str) -> GitOperationResult:
        return await self._git(["switch", "-c", branch], workspace)

    async def write_files(self, workspace: Path, files: dict[str, str]) -> None:
        root = workspace.resolve()
        for relative, content in files.items():
            target = (root / relative).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"Path escapes workspace: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    async def commit(self, workspace: Path, message: str) -> GitOperationResult:
        added = await self._git(["add", "--all"], workspace)
        if not added.success:
            return added
        return await self._git(["commit", "-m", message], workspace)

    async def push(self, workspace: Path, branch: str) -> GitOperationResult:
        return await self._git(["push", "--set-upstream", "origin", branch], workspace)

    async def open_pull_request(
        self,
        repository: GitHubRepository,
        title: str,
        branch: str,
        body: str = "",
    ):
        return await self.github.open_pull_request(
            repository, title=title, head=branch, body=body
        )

    async def _git(self, args: list[str], cwd: Path) -> GitOperationResult:
        def run() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [self.git_executable, *args],
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )

        try:
            result = await asyncio.to_thread(run)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return GitOperationResult(False, str(exc))
        output = (result.stdout + result.stderr).strip()
        return GitOperationResult(
            result.returncode == 0,
            output or ("Git operation completed" if result.returncode == 0 else "Git operation failed"),
            output,
        )
