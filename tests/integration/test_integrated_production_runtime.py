import asyncio

import pytest

from src.company.runtime import IntegratedProductionRuntime


@pytest.mark.asyncio
async def test_integrated_runtime_starts_and_stops():
    runtime = IntegratedProductionRuntime()

    await runtime.start()

    state = await runtime.state()

    assert state.running is True
    assert state.worker_count == 1

    await runtime.stop()

    state = await runtime.state()

    assert state.running is False


@pytest.mark.asyncio
async def test_integrated_runtime_executes_work():
    runtime = IntegratedProductionRuntime(worker_count=2)
    completed: list[int] = []

    async def operation() -> None:
        await asyncio.sleep(0.01)
        completed.append(1)

    await runtime.start()

    for _ in range(5):
        await runtime.submit(operation)

    await runtime.wait()

    state = await runtime.state()

    assert len(completed) == 5
    assert state.processed == 5
    assert state.failed == 0

    await runtime.stop()


@pytest.mark.asyncio
async def test_integrated_runtime_rejects_submit_when_stopped():
    runtime = IntegratedProductionRuntime()

    async def operation() -> None:
        pass

    with pytest.raises(RuntimeError, match="not running"):
        await runtime.submit(operation)


@pytest.mark.asyncio
async def test_integrated_runtime_validates_configuration():
    with pytest.raises(ValueError, match="max_queue_size"):
        IntegratedProductionRuntime(max_queue_size=0)

    with pytest.raises(ValueError, match="worker_count"):
        IntegratedProductionRuntime(worker_count=0)


@pytest.mark.asyncio
async def test_integrated_runtime_tracks_failed_operation():
    runtime = IntegratedProductionRuntime()

    async def operation() -> None:
        raise ValueError("expected failure")

    await runtime.start()
    await runtime.submit(operation)
    await runtime.wait()

    state = await runtime.state()

    assert state.failed == 1

    await runtime.stop()
