from pathlib import Path
import subprocess

import pytest

from src.tools.builtin.git_write import GitWriteTools


def init_repo(path: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    )

    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
    )

    subprocess.run(
        ["git", "config", "user.name", "Test Agent"],
        cwd=path,
        check=True,
    )


def test_git_commit(tmp_path: Path) -> None:
    init_repo(tmp_path)

    (tmp_path / "hello.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    tools = GitWriteTools(tmp_path)

    output = tools.commit("test commit")

    assert "test commit" in output

    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "test commit"


def test_empty_commit_message_rejected(tmp_path: Path) -> None:
    init_repo(tmp_path)

    tools = GitWriteTools(tmp_path)

    with pytest.raises(ValueError):
        tools.commit("")


def test_git_push_requires_remote(tmp_path: Path) -> None:
    init_repo(tmp_path)

    tools = GitWriteTools(tmp_path)

    with pytest.raises(RuntimeError):
        tools.push()


def test_git_commit_does_not_accept_empty_message(tmp_path: Path) -> None:
    init_repo(tmp_path)

    tools = GitWriteTools(tmp_path)

    with pytest.raises(ValueError):
        tools.commit("   ")
