import asyncio

import pytest

from company.runtime.execution_result import AutonomousExecutionStatus
from company.runtime.executor import AutonomousExecutor


@pytest.mark.asyncio
async def test_executor_runs_real_pipeline():
    calls = []

    async def pipeline(mission):
        calls.append(mission)
        await asyncio.sleep(0.01)
        return {"mission": mission, "success": True}

    executor = AutonomousExecutor(pipeline)

    accepted = await executor.execute("run-1", "build an application")

    assert accepted.run_id == "run-1"
    assert accepted.status == AutonomousExecutionStatus.ACCEPTED

    result = await executor.wait("run-1")

    assert result.status == AutonomousExecutionStatus.COMPLETED
    assert result.result == {
        "mission": "build an application",
        "success": True,
    }
    assert calls == ["build an application"]


@pytest.mark.asyncio
async def test_executor_reports_pipeline_failure():
    async def pipeline(_mission):
        raise RuntimeError("pipeline failed")

    executor = AutonomousExecutor(pipeline)

    await executor.execute("run-2", "broken mission")

    result = await executor.wait("run-2")

    assert result.status == AutonomousExecutionStatus.FAILED
    assert result.error == "pipeline failed"


@pytest.mark.asyncio
async def test_executor_rejects_duplicate_run():
    async def pipeline(_mission):
        await asyncio.sleep(0.05)

    executor = AutonomousExecutor(pipeline)

    await executor.execute("run-3", "mission")

    with pytest.raises(ValueError, match="run already exists"):
        await executor.execute("run-3", "mission")


@pytest.mark.asyncio
async def test_executor_rejects_unknown_wait():
    async def pipeline(_mission):
        return None

    executor = AutonomousExecutor(pipeline)

    with pytest.raises(KeyError):
        await executor.wait("unknown")


@pytest.mark.asyncio
async def test_executor_reports_running_state():
    gate = asyncio.Event()

    async def pipeline(_mission):
        await gate.wait()
        return "done"

    executor = AutonomousExecutor(pipeline)

    await executor.execute("run-4", "mission")

    await asyncio.sleep(0)

    assert executor.running("run-4") is True

    gate.set()

    result = await executor.wait("run-4")

    assert result.status == AutonomousExecutionStatus.COMPLETED
    assert executor.running("run-4") is False


@pytest.mark.asyncio
async def test_executor_requires_nonempty_run_id():
    async def pipeline(_mission):
        return None

    executor = AutonomousExecutor(pipeline)

    with pytest.raises(ValueError, match="run_id"):
        await executor.execute("", "mission")
