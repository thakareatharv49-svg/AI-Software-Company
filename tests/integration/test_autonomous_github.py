import sys

import pytest

from company.runtime.autonomous_github import (
    AutomationStatus,
    AutonomousGitHubAutomation,
)
from company.runtime.github_client import (
    GitHubPullRequest,
    GitHubRepository,
)
from company.runtime.qa_runner import (
    AutonomousQARunner,
    QARunStatus,
)


class FakeGitHub:
    def __init__(self):
        self.branches = []
        self.pull_requests = []
        self.merged = []

    def auth_status(self):
        return True

    def repository(self, owner, name):
        return GitHubRepository(
            owner=owner,
            name=name,
            default_branch="main",
            url=f"https://github.com/{owner}/{name}",
        )

    def create_branch(self, owner, name, branch, base):
        self.branches.append((owner, name, branch, base))

    async def acreate_pull_request(
        self,
        owner,
        name,
        title,
        body,
        head,
        base,
    ):
        self.pull_requests.append(
            (owner, name, title, body, head, base)
        )
        return GitHubPullRequest(
            number=42,
            title=title,
            url=f"https://github.com/{owner}/{name}/pull/42",
            state="OPEN",
        )

    def merge_pull_request(self, owner, name, number):
        self.merged.append((owner, name, number))


def python_command(code):
    return (sys.executable, "-c", code)


@pytest.mark.asyncio
async def test_successful_automation_creates_pr():
    github = FakeGitHub()
    automation = AutonomousGitHubAutomation(
        github=github,
        qa=AutonomousQARunner(timeout_seconds=5),
    )

    result = await automation.execute(
        run_id="auto-1",
        owner="acme",
        repository="app",
        branch="ai/change-1",
        title="Autonomous change",
        body="Created by autonomous execution.",
        commands=[
            python_command("print('qa ok')"),
        ],
    )

    assert result.status == AutomationStatus.PR_CREATED
    assert result.qa_run is not None
    assert result.qa_run.status == QARunStatus.PASSED
    assert result.pull_request is not None
    assert result.pull_request.number == 42
    assert len(github.branches) == 1
    assert len(github.pull_requests) == 1
    assert github.merged == []


@pytest.mark.asyncio
async def test_failed_qa_does_not_create_pr():
    github = FakeGitHub()
    automation = AutonomousGitHubAutomation(
        github=github,
        qa=AutonomousQARunner(timeout_seconds=5),
    )

    result = await automation.execute(
        run_id="auto-2",
        owner="acme",
        repository="app",
        branch="ai/change-2",
        title="Should fail",
        body="",
        commands=[
            python_command("import sys; sys.exit(3)"),
        ],
    )

    assert result.status == AutomationStatus.FAILED
    assert result.pull_request is None
    assert github.branches == []
    assert github.pull_requests == []


@pytest.mark.asyncio
async def test_merge_after_success():
    github = FakeGitHub()
    automation = AutonomousGitHubAutomation(
        github=github,
        qa=AutonomousQARunner(timeout_seconds=5),
    )

    result = await automation.execute(
        run_id="auto-3",
        owner="acme",
        repository="app",
        branch="ai/change-3",
        title="Merge me",
        body="",
        commands=[
            python_command("print('ok')"),
        ],
        merge=True,
    )

    assert result.status == AutomationStatus.MERGED
    assert github.merged == [("acme", "app", 42)]


@pytest.mark.asyncio
async def test_auth_failure_stops_automation():
    github = FakeGitHub()
    github.auth_status = lambda: False

    automation = AutonomousGitHubAutomation(
        github=github,
        qa=AutonomousQARunner(timeout_seconds=5),
    )

    result = await automation.execute(
        run_id="auto-4",
        owner="acme",
        repository="app",
        branch="ai/change-4",
        title="Auth failure",
        body="",
        commands=[
            python_command("print('must not execute')"),
        ],
    )

    assert result.status == AutomationStatus.FAILED
    assert "authentication" in result.error.lower()
    assert result.pull_request is None


@pytest.mark.asyncio
async def test_unknown_run():
    automation = AutonomousGitHubAutomation(
        github=FakeGitHub(),
        qa=AutonomousQARunner(timeout_seconds=5),
    )

    with pytest.raises(KeyError):
        automation.get_run("missing")


@pytest.mark.asyncio
async def test_duplicate_run_rejected():
    automation = AutonomousGitHubAutomation(
        github=FakeGitHub(),
        qa=AutonomousQARunner(timeout_seconds=5),
    )

    await automation.execute(
        run_id="duplicate",
        owner="acme",
        repository="app",
        branch="ai/change",
        title="First",
        body="",
        commands=[python_command("print('ok')")],
    )

    with pytest.raises(ValueError):
        await automation.execute(
            run_id="duplicate",
            owner="acme",
            repository="app",
            branch="ai/change-2",
            title="Second",
            body="",
            commands=[python_command("print('ok')")],
        )
