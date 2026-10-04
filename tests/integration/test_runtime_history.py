from __future__ import annotations

import asyncio

import pytest

from company.runtime.history import (
    RuntimeExecutionHistory,
    TrackedProductionRuntime,
)


class FakeRuntime:
    async def execute(self, operation):
        return await operation()


@pytest.mark.asyncio
async def test_execution_history_tracks_completion() -> None:
    history = RuntimeExecutionHistory()
    runtime = TrackedProductionRuntime(FakeRuntime(), history)

    result = await runtime.execute(lambda: asyncio.sleep(0, result="success"))

    assert result == "success"

    records = await history.records()

    assert len(records) == 1
    assert records[0].execution_id == "runtime-execution-1"
    assert records[0].status == "completed"
    assert records[0].completed_at is not None
    assert records[0].error is None


@pytest.mark.asyncio
async def test_execution_history_tracks_failure() -> None:
    history = RuntimeExecutionHistory()
    runtime = TrackedProductionRuntime(FakeRuntime(), history)

    async def operation():
        raise RuntimeError("execution failed")

    with pytest.raises(RuntimeError, match="execution failed"):
        await runtime.execute(operation)

    record = await history.get("runtime-execution-1")

    assert record is not None
    assert record.status == "failed"
    assert record.completed_at is not None
    assert record.error == "execution failed"


@pytest.mark.asyncio
async def test_execution_history_tracks_multiple_executions() -> None:
    history = RuntimeExecutionHistory()
    runtime = TrackedProductionRuntime(FakeRuntime(), history)

    async def operation():
        return "ok"

    await runtime.execute(operation)
    await runtime.execute(operation)

    records = await history.records()

    assert len(records) == 2
    assert [record.execution_id for record in records] == [
        "runtime-execution-1",
        "runtime-execution-2",
    ]


@pytest.mark.asyncio
async def test_unknown_execution_cannot_be_updated() -> None:
    history = RuntimeExecutionHistory()

    with pytest.raises(KeyError):
        await history.complete("missing-execution")
