from pathlib import Path
import subprocess

from src.tools.builtin.git import GitTools


def test_git_status(tmp_path: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    tools = GitTools(tmp_path)

    assert tools.status() == ""


def test_git_diff(tmp_path: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    file = tmp_path / "test.txt"
    file.write_text("hello", encoding="utf-8")

    tools = GitTools(tmp_path)

    output = tools.diff()

    assert isinstance(output, str)
