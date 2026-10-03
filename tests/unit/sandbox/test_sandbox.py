from pathlib import Path

import pytest

from src.sandbox import (
    SandboxExecutor,
    SandboxLimits,
    SandboxRequest,
    SandboxStatus,
)


@pytest.mark.asyncio
async def test_sandbox_executes_allowed_python():
    executor = SandboxExecutor()

    request = SandboxRequest(
        command=["python", "-c", "print('sandbox-ok')"],
        working_directory=str(Path.cwd()),
    )

    result = await executor.execute(request)

    assert result.status == SandboxStatus.SUCCESS
    assert "sandbox-ok" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_blocks_unknown_command():
    executor = SandboxExecutor()

    request = SandboxRequest(
        command=["powershell", "-Command", "Write-Output blocked"],
        working_directory=str(Path.cwd()),
    )

    with pytest.raises(PermissionError):
        await executor.execute(request)


@pytest.mark.asyncio
async def test_sandbox_reports_failure():
    executor = SandboxExecutor()

    request = SandboxRequest(
        command=["python", "-c", "raise SystemExit(3)"],
        working_directory=str(Path.cwd()),
    )

    result = await executor.execute(request)

    assert result.status == SandboxStatus.FAILED
    assert result.exit_code == 3


@pytest.mark.asyncio
async def test_sandbox_timeout():
    executor = SandboxExecutor()

    request = SandboxRequest(
        command=[
            "python",
            "-c",
            "import time; time.sleep(2)",
        ],
        working_directory=str(Path.cwd()),
        limits=SandboxLimits(timeout_seconds=0.1),
    )

    result = await executor.execute(request)

    assert result.status == SandboxStatus.TIMEOUT


@pytest.mark.asyncio
async def test_sandbox_missing_directory():
    executor = SandboxExecutor()

    request = SandboxRequest(
        command=["python", "-c", "print('test')"],
        working_directory=str(Path.cwd() / "does-not-exist"),
    )

    with pytest.raises(FileNotFoundError):
        await executor.execute(request)
