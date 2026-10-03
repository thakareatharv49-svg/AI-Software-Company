import httpx
import pytest

from src.github.client.api import GitHubAPIClient, GitHubAPIError
from src.github.models.contracts import GitHubIssue, GitHubPullRequest, GitHubRepository


@pytest.mark.asyncio
async def test_get_repository() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/repos/acme/demo"

        return httpx.Response(
            200,
            json={
                "owner": {"login": "acme"},
                "name": "demo",
                "default_branch": "master",
            },
        )

    transport = httpx.MockTransport(handler)

    async with GitHubAPIClient(
        "test-token",
        transport=transport,
    ) as client:
        repository = await client.get_repository("acme", "demo")

    assert repository.owner == "acme"
    assert repository.name == "demo"
    assert repository.default_branch == "master"


@pytest.mark.asyncio
async def test_create_issue_requires_write_permission() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(201, json={"number": 1})
    )

    async with GitHubAPIClient(
        "test-token",
        transport=transport,
    ) as client:
        with pytest.raises(GitHubAPIError, match="allow_writes"):
            await client.create_issue(
                GitHubRepository(owner="acme", name="demo"),
                GitHubIssue(title="Test"),
            )


@pytest.mark.asyncio
async def test_create_issue() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/repos/acme/demo/issues"

        payload = request.read()
        assert b'"title":"Test"' in payload

        return httpx.Response(201, json={"number": 42})

    async with GitHubAPIClient(
        "test-token",
        allow_writes=True,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.create_issue(
            GitHubRepository(owner="acme", name="demo"),
            GitHubIssue(title="Test"),
        )

    assert result.success is True
    assert result.identifier == "42"


@pytest.mark.asyncio
async def test_create_pull_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/repos/acme/demo/pulls"

        return httpx.Response(201, json={"number": 7})

    async with GitHubAPIClient(
        "test-token",
        allow_writes=True,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.create_pull_request(
            GitHubRepository(owner="acme", name="demo"),
            GitHubPullRequest(
                title="Feature",
                head="feature/test",
                base="main",
            ),
        )

    assert result.success is True
    assert result.identifier == "7"


@pytest.mark.asyncio
async def test_get_branch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "name": "main",
                "commit": {"sha": "abc123"},
            },
        )

    async with GitHubAPIClient(
        "test-token",
        transport=httpx.MockTransport(handler),
    ) as client:
        branch = await client.get_branch(
            GitHubRepository(owner="acme", name="demo"),
            "main",
        )

    assert branch.name == "main"
    assert branch.sha == "abc123"


@pytest.mark.asyncio
async def test_create_branch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/repos/acme/demo/git/refs"

        return httpx.Response(
            201,
            json={"ref": "refs/heads/feature/test"},
        )

    async with GitHubAPIClient(
        "test-token",
        allow_writes=True,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.create_branch(
            GitHubRepository(owner="acme", name="demo"),
            "feature/test",
            "abc123",
        )

    assert result.success is True
    assert result.identifier == "refs/heads/feature/test"


@pytest.mark.asyncio
async def test_get_file_decodes_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "type": "file",
                "path": "README.md",
                "sha": "file123",
                "content": "SGVsbG8gd29ybGQ=",
            },
        )

    async with GitHubAPIClient(
        "test-token",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.get_file(
            GitHubRepository(owner="acme", name="demo"),
            "README.md",
        )

    assert result.path == "README.md"
    assert result.content == "Hello world"
    assert result.sha == "file123"


@pytest.mark.asyncio
async def test_write_file() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/repos/acme/demo/contents/README.md"

        return httpx.Response(
            200,
            json={"commit": {"sha": "commit123"}},
        )

    async with GitHubAPIClient(
        "test-token",
        allow_writes=True,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.write_file(
            GitHubRepository(owner="acme", name="demo"),
            "README.md",
            "Hello",
            "Update README",
            "main",
        )

    assert result.success is True
    assert result.identifier == "commit123"


@pytest.mark.asyncio
async def test_get_check_runs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "check_runs": [
                    {
                        "name": "tests",
                        "status": "completed",
                        "conclusion": "success",
                    },
                ],
            },
        )

    async with GitHubAPIClient(
        "test-token",
        transport=httpx.MockTransport(handler),
    ) as client:
        checks = await client.get_check_runs(
            GitHubRepository(owner="acme", name="demo"),
            "abc123",
        )

    assert len(checks) == 1
    assert checks[0].name == "tests"
    assert checks[0].conclusion == "success"


@pytest.mark.asyncio
async def test_github_api_error() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            404,
            json={"message": "Not Found"},
        )
    )

    async with GitHubAPIClient(
        "test-token",
        transport=transport,
    ) as client:
        with pytest.raises(
            GitHubAPIError,
            match="404: Not Found",
        ):
            await client.get_repository("acme", "missing")
