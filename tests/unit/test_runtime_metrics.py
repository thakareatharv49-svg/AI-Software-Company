import asyncio

import pytest

from src.company.runtime import (
    InstrumentedRuntimeExecutor,
    RuntimeMetricsCollector,
)


@pytest.mark.asyncio
async def test_metrics_track_successful_execution() -> None:
    metrics = RuntimeMetricsCollector()

    async def operation() -> str:
        return "ok"

    executor = InstrumentedRuntimeExecutor(operation, metrics)

    assert await executor.execute() == "ok"

    snapshot = await metrics.snapshot()

    assert snapshot.total_started == 1
    assert snapshot.total_completed == 1
    assert snapshot.total_failed == 0
    assert snapshot.active_tasks == 0


@pytest.mark.asyncio
async def test_metrics_track_failed_execution() -> None:
    metrics = RuntimeMetricsCollector()

    async def operation() -> None:
        raise RuntimeError("failure")

    executor = InstrumentedRuntimeExecutor(operation, metrics)

    with pytest.raises(RuntimeError, match="failure"):
        await executor.execute()

    snapshot = await metrics.snapshot()

    assert snapshot.total_started == 1
    assert snapshot.total_completed == 0
    assert snapshot.total_failed == 1
    assert snapshot.active_tasks == 0


@pytest.mark.asyncio
async def test_metrics_track_cancellation() -> None:
    metrics = RuntimeMetricsCollector()
    started = asyncio.Event()
    release = asyncio.Event()

    async def operation() -> None:
        started.set()
        await release.wait()

    executor = InstrumentedRuntimeExecutor(operation, metrics)
    task = asyncio.create_task(executor.execute())

    await started.wait()

    snapshot = await metrics.snapshot()
    assert snapshot.total_started == 1
    assert snapshot.active_tasks == 1

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    snapshot = await metrics.snapshot()

    assert snapshot.total_failed == 1
    assert snapshot.active_tasks == 0


@pytest.mark.asyncio
async def test_metrics_track_multiple_executions() -> None:
    metrics = RuntimeMetricsCollector()

    async def operation() -> str:
        return "done"

    executor = InstrumentedRuntimeExecutor(operation, metrics)

    await asyncio.gather(
        executor.execute(),
        executor.execute(),
        executor.execute(),
    )

    snapshot = await metrics.snapshot()

    assert snapshot.total_started == 3
    assert snapshot.total_completed == 3
    assert snapshot.total_failed == 0
    assert snapshot.active_tasks == 0


@pytest.mark.asyncio
async def test_metrics_do_not_allow_negative_active_tasks() -> None:
    metrics = RuntimeMetricsCollector()

    await metrics.completed()
    await metrics.failed()

    snapshot = await metrics.snapshot()

    assert snapshot.active_tasks == 0
