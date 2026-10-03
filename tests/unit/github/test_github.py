import pytest

from src.github.automation.automation import GitHubAutomation
from src.github.client.memory import InMemoryGitHubClient
from src.github.models.contracts import GitHubRepository


@pytest.mark.asyncio
async def test_github_creates_task_issue():
    client = InMemoryGitHubClient()
    automation = GitHubAutomation(client)
    repository = GitHubRepository(owner="test", name="company")

    result = await automation.open_task_issue(
        repository,
        "Implement scheduler",
        "Build the task scheduler.",
    )

    assert result.success is True
    assert result.identifier == "issue-1"
    assert len(client.issues) == 1
    assert "task" in client.issues[0].labels


@pytest.mark.asyncio
async def test_github_creates_pull_request():
    client = InMemoryGitHubClient()
    automation = GitHubAutomation(client)
    repository = GitHubRepository(owner="test", name="company")

    result = await automation.open_pull_request(
        repository,
        "Add scheduler",
        "feature/scheduler",
    )

    assert result.success is True
    assert result.identifier == "pr-1"
    assert client.pull_requests[0].base == "main"


@pytest.mark.asyncio
async def test_github_repository_lookup():
    client = InMemoryGitHubClient()

    repository = await client.get_repository("test", "company")

    assert repository.owner == "test"
    assert repository.name == "company"
