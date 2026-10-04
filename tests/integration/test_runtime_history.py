import pytest

from src.company.runtime import (
    ProductionRuntime,
    RuntimeConfig,
    RuntimeExecutionHistory,
    TrackedProductionRuntime,
)


def make_runtime() -> ProductionRuntime:
    return ProductionRuntime(
        RuntimeConfig(
            environment="test",
            host="127.0.0.1",
            port=8000,
            debug=False,
            max_concurrent_runs=1,
            shutdown_timeout_seconds=1,
        )
    )


@pytest.mark.asyncio
async def test_history_tracks_completed_execution() -> None:
    runtime = make_runtime()
    history = RuntimeExecutionHistory()
    tracked = TrackedProductionRuntime(runtime, history)

    await runtime.start()

    async def operation() -> str:
        return "success"

    result = await tracked.execute(operation)

    assert result.completed is True

    records = await history.records()

    assert len(records) == 1
    assert records[0].status == "completed"
    assert records[0].completed_at is not None
    assert records[0].error is None

    await runtime.stop()


@pytest.mark.asyncio
async def test_history_tracks_failed_execution() -> None:
    runtime = make_runtime()
    history = RuntimeExecutionHistory()
    tracked = TrackedProductionRuntime(runtime, history)

    await runtime.start()

    async def operation() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await tracked.execute(operation)

    records = await history.records()

    assert len(records) == 1
    assert records[0].status == "failed"
    assert records[0].error == "boom"
    assert records[0].completed_at is not None

    await runtime.stop()


@pytest.mark.asyncio
async def test_history_generates_unique_execution_ids() -> None:
    runtime = make_runtime()
    history = RuntimeExecutionHistory()
    tracked = TrackedProductionRuntime(runtime, history)

    await runtime.start()

    async def operation() -> str:
        return "ok"

    await tracked.execute(operation)
    await tracked.execute(operation)

    records = await history.records()

    assert len(records) == 2
    assert records[0].execution_id != records[1].execution_id

    await runtime.stop()


@pytest.mark.asyncio
async def test_history_get_returns_latest_record() -> None:
    history = RuntimeExecutionHistory()

    await history.start("execution-1")
    completed = await history.complete("execution-1")

    result = await history.get("execution-1")

    assert result == completed
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_history_unknown_execution_raises() -> None:
    history = RuntimeExecutionHistory()

    with pytest.raises(KeyError, match="unknown execution_id"):
        await history.complete("missing")


@pytest.mark.asyncio
async def test_history_unknown_get_returns_none() -> None:
    history = RuntimeExecutionHistory()

    assert await history.get("missing") is None
