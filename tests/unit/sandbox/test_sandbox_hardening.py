from pathlib import Path

import pytest

from src.sandbox import (
    SandboxExecutor,
    SandboxLimits,
    SandboxRequest,
    SandboxStatus,
)
from src.tools.builtin.commands import CommandTools


@pytest.mark.asyncio
async def test_sandbox_enforces_workspace_boundary(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    executor = SandboxExecutor(workspace=workspace)

    request = SandboxRequest(
        command=["python", "-c", "print('blocked')"],
        working_directory=str(outside),
    )

    with pytest.raises(PermissionError):
        await executor.execute(request)


@pytest.mark.asyncio
async def test_sandbox_enforces_output_limit(tmp_path: Path) -> None:
    executor = SandboxExecutor()

    request = SandboxRequest(
        command=[
            "python",
            "-c",
            "print('x' * 1000)",
        ],
        working_directory=str(tmp_path),
        limits=SandboxLimits(max_output_bytes=100),
    )

    result = await executor.execute(request)

    assert result.status == SandboxStatus.SUCCESS
    assert len(result.stdout.encode("utf-8")) <= 100


@pytest.mark.asyncio
async def test_sandbox_sanitizes_environment(tmp_path: Path) -> None:
    import os

    original = os.environ.get("SANDBOX_SECRET_TEST")

    try:
        os.environ["SANDBOX_SECRET_TEST"] = "should-not-leak"

        executor = SandboxExecutor()

        request = SandboxRequest(
            command=[
                "python",
                "-c",
                (
                    "import os; "
                    "print(os.getenv('SANDBOX_SECRET_TEST', 'MISSING'))"
                ),
            ],
            working_directory=str(tmp_path),
        )

        result = await executor.execute(request)

        assert result.status == SandboxStatus.SUCCESS
        assert "should-not-leak" not in result.stdout
        assert "MISSING" in result.stdout
    finally:
        if original is None:
            os.environ.pop("SANDBOX_SECRET_TEST", None)
        else:
            os.environ["SANDBOX_SECRET_TEST"] = original


def test_command_tools_enforces_output_limit(tmp_path: Path) -> None:
    tools = CommandTools(
        tmp_path,
        max_output_chars=100,
    )

    output = tools.run_command(
        "python",
        ["-c", "print('x' * 1000)"],
    )

    assert len(output) <= 100


def test_command_tools_cannot_escape_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    executor = SandboxExecutor(workspace=workspace)

    request = SandboxRequest(
        command=["python", "-c", "print('outside')"],
        working_directory=str(outside),
    )

    with pytest.raises(PermissionError):
        executor.execute_sync(request)


def test_command_tools_uses_sandbox_environment(tmp_path: Path) -> None:
    import os

    original = os.environ.get("SANDBOX_COMMAND_SECRET")

    try:
        os.environ["SANDBOX_COMMAND_SECRET"] = "hidden-value"

        tools = CommandTools(tmp_path)

        output = tools.run_command(
            "python",
            [
                "-c",
                (
                    "import os; "
                    "print(os.getenv('SANDBOX_COMMAND_SECRET', 'MISSING'))"
                ),
            ],
        )

        assert "hidden-value" not in output
        assert "MISSING" in output
    finally:
        if original is None:
            os.environ.pop("SANDBOX_COMMAND_SECRET", None)
        else:
            os.environ["SANDBOX_COMMAND_SECRET"] = original
