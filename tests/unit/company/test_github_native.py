from pathlib import Path
from types import SimpleNamespace

import pytest

from src.company.github_native import GitHubNativeService
from src.github.models.contracts import GitHubRepository


class FakeGitHub:
    async def open_pull_request(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_github_native_writes_only_inside_workspace(tmp_path: Path):
    service = GitHubNativeService(github=FakeGitHub())
    await service.write_files(tmp_path, {"src/main.py": "print('ok')"})

    assert (tmp_path / "src/main.py").read_text(encoding="utf-8") == "print('ok')"

    with pytest.raises(ValueError):
        await service.write_files(tmp_path, {"../escape.py": "bad"})


class FakePublishingClient:
    def __init__(self):
        self.branches_checked = []
        self.published_entries = []
        self.updated_branch = None

    async def get_repository(self, owner, name):
        return GitHubRepository(owner=owner, name=name, default_branch="main")

    async def get_branch(self, repository, branch):
        self.branches_checked.append(branch)
        if branch != "main":
            raise RuntimeError("GitHub API 404: branch not found")
        return SimpleNamespace(sha="base-sha")

    async def create_tree(self, repository, base_tree_sha, entries):
        self.published_entries = entries
        assert base_tree_sha == "base-sha"
        return "tree-sha"

    async def create_commit(self, repository, message, tree_sha, parent_sha):
        assert tree_sha == "tree-sha"
        assert parent_sha == "base-sha"
        return "new-commit-sha"

    async def update_branch_ref(self, repository, branch, commit_sha, expected_sha):
        self.updated_branch = branch
        assert commit_sha == "new-commit-sha"
        assert expected_sha == "base-sha"


class FakePublishingGitHub:
    def __init__(self):
        self.client = FakePublishingClient()


@pytest.mark.asyncio
async def test_publish_falls_back_to_repository_default_branch():
    github = FakePublishingGitHub()
    service = GitHubNativeService(github=github)

    result = await service.publish_files(
        GitHubRepository(owner="owner", name="notes-app", default_branch="main"),
        "master",
        {"index.html": "<!doctype html><title>Notes</title>", "app.js": "console.log('notes')"},
        "feat: publish notes app",
    )

    assert result.success is True
    assert "2 file(s)" in result.message
    assert ":main" in result.message
    assert github.client.branches_checked == ["master", "main"]
    assert github.client.updated_branch == "main"
    assert {entry["path"] for entry in github.client.published_entries} == {
        "index.html",
        "app.js",
    }


@pytest.mark.asyncio
async def test_publish_rejects_empty_generated_project():
    service = GitHubNativeService(github=FakePublishingGitHub())

    result = await service.publish_files(
        GitHubRepository(owner="owner", name="empty-app"),
        "main",
        {},
        "feat: publish generated app",
    )

    assert result.success is False
    assert "empty generated project" in result.message
