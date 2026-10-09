import sys

import pytest

from src.sandbox.execution.executor import SandboxExecutor
from src.sandbox.models.contracts import SandboxRequest
from src.sandbox.models.enums import SandboxStatus


@pytest.mark.asyncio
async def test_async_execute_runs_python_command_without_event_loop_subprocess(
    tmp_path,
):
    executor = SandboxExecutor()
    request = SandboxRequest(
        command=[sys.executable, "-c", "print('sandbox-ok')"],
        working_directory=str(tmp_path),
    )

    result = await executor.execute(request)

    assert result.status == SandboxStatus.SUCCESS
    assert result.exit_code == 0
    assert result.stdout.strip() == "sandbox-ok"
