from src.config.settings import Settings
from src.github.client.api import GitHubAPIClient
from src.github.client.memory import InMemoryGitHubClient
from src.github.factory import create_github_client


def test_factory_creates_memory_client_for_test_environment(monkeypatch):
    monkeypatch.setattr(
        "src.github.factory.settings",
        Settings(
            environment="test",
            github_token="",
        ),
    )

    client = create_github_client()

    assert isinstance(client, InMemoryGitHubClient)


def test_factory_creates_real_client(monkeypatch):
    monkeypatch.setattr(
        "src.github.factory.settings",
        Settings(
            environment="development",
            github_token="test-token",
            github_api_base_url="https://api.github.com",
            github_timeout=15.0,
            github_allow_writes=False,
        ),
    )

    client = create_github_client()

    assert isinstance(client, GitHubAPIClient)
    assert client.allow_writes is False


def test_factory_blocks_real_client_without_token(monkeypatch):
    monkeypatch.setattr(
        "src.github.factory.settings",
        Settings(
            environment="development",
            github_token="",
        ),
    )

    try:
        create_github_client()
    except Exception as exc:
        assert "GitHub token is not configured" in str(exc)
    else:
        raise AssertionError("Expected GitHub token configuration error")
