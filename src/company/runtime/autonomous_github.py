from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from .github_client import GitHubClient, GitHubPullRequest
from .qa_runner import AutonomousQARunner, QARun


class AutomationStatus(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    QA_PASSED = "qa_passed"
    PR_CREATED = "pr_created"
    MERGED = "merged"
    FAILED = "failed"


@dataclass
class AutonomousGitHubRun:
    run_id: str
    status: AutomationStatus
    qa_run: QARun | None = None
    pull_request: GitHubPullRequest | None = None
    error: str | None = None


class AutonomousGitHubAutomation:
    def __init__(
        self,
        github: GitHubClient | None = None,
        qa: AutonomousQARunner | None = None,
    ) -> None:
        self.github = github or GitHubClient()
        self.qa = qa or AutonomousQARunner()
        self._runs: dict[str, AutonomousGitHubRun] = {}

    def get_run(self, run_id: str) -> AutonomousGitHubRun:
        if run_id not in self._runs:
            raise KeyError(run_id)
        return self._runs[run_id]

    async def execute(
        self,
        run_id: str,
        owner: str,
        repository: str,
        branch: str,
        title: str,
        body: str,
        commands: Sequence[Sequence[str]],
        merge: bool = False,
    ) -> AutonomousGitHubRun:
        if run_id in self._runs:
            raise ValueError(f"Run already exists: {run_id}")

        run = AutonomousGitHubRun(
            run_id=run_id,
            status=AutomationStatus.ACCEPTED,
        )
        self._runs[run_id] = run

        try:
            run.status = AutomationStatus.RUNNING

            if not self.github.auth_status():
                raise RuntimeError("GitHub authentication is unavailable")

            repo = self.github.repository(owner, repository)

            await self.qa.run(run_id, commands)
            run.qa_run = self.qa.get_run(run_id)

            if not run.qa_run.passed:
                run.status = AutomationStatus.FAILED
                run.error = "Autonomous QA failed"
                return run

            run.status = AutomationStatus.QA_PASSED

            self.github.create_branch(
                owner,
                repository,
                branch,
                repo.default_branch,
            )

            run.pull_request = await self.github.acreate_pull_request(
                owner,
                repository,
                title,
                body,
                branch,
                repo.default_branch,
            )

            run.status = AutomationStatus.PR_CREATED

            if merge:
                self.github.merge_pull_request(
                    owner,
                    repository,
                    run.pull_request.number,
                )
                run.status = AutomationStatus.MERGED

            return run

        except Exception as exc:
            run.status = AutomationStatus.FAILED
            run.error = str(exc)
            return run


async def run_automation(
    automation: AutonomousGitHubAutomation,
    run_id: str,
    owner: str,
    repository: str,
    branch: str,
    title: str,
    body: str,
    commands: Sequence[Sequence[str]],
    merge: bool = False,
) -> AutonomousGitHubRun:
    return await automation.execute(
        run_id=run_id,
        owner=owner,
        repository=repository,
        branch=branch,
        title=title,
        body=body,
        commands=commands,
        merge=merge,
    )
