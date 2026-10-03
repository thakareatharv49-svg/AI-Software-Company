from pathlib import Path

import pytest

from src.tools.builtin.commands import CommandTools


def test_allowed_python_command(tmp_path: Path) -> None:
    tools = CommandTools(tmp_path)

    output = tools.run_command(
        "python",
        ["-c", "print('hello')"],
    )

    assert "hello" in output


def test_disallowed_command(tmp_path: Path) -> None:
    tools = CommandTools(tmp_path)

    with pytest.raises(PermissionError):
        tools.run_command("powershell", ["-Command", "Write-Output hello"])


def test_command_runs_inside_workspace(tmp_path: Path) -> None:
    tools = CommandTools(tmp_path)

    output = tools.run_command(
        "python",
        ["-c", "import os; print(os.getcwd())"],
    )

    assert str(tmp_path) in output


def test_command_timeout(tmp_path: Path) -> None:
    tools = CommandTools(
        tmp_path,
        timeout_seconds=1,
    )

    with pytest.raises(TimeoutError):
        tools.run_command(
            "python",
            ["-c", "import time; time.sleep(3)"],
        )
