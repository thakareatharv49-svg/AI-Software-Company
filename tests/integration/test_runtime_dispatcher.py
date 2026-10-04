from __future__ import annotations

import asyncio

import pytest

from company.runtime.dispatcher import RuntimeDispatcher


@pytest.mark.asyncio
async def test_dispatcher_starts_and_stops() -> None:
    dispatcher = RuntimeDispatcher(
        max_queue_size=10,
        worker_count=2,
    )

    await dispatcher.start()

    state = await dispatcher.state()

    assert state.running is True
    assert state.worker_count == 2
    assert state.queued == 0

    await dispatcher.stop()

    state = await dispatcher.state()

    assert state.running is False


@pytest.mark.asyncio
async def test_dispatcher_executes_submitted_operations() -> None:
    dispatcher = RuntimeDispatcher(
        max_queue_size=10,
        worker_count=2,
    )

    completed = 0
    lock = asyncio.Lock()

    async def operation():
        nonlocal completed

        await asyncio.sleep(0)

        async with lock:
            completed += 1

    await dispatcher.start()

    for _ in range(5):
        await dispatcher.submit(operation)

    await dispatcher.wait()
    await dispatcher.stop()

    state = await dispatcher.state()

    assert completed == 5
    assert state.processed == 5
    assert state.failed == 0
    assert state.queued == 0


@pytest.mark.asyncio
async def test_dispatcher_runs_operations_concurrently() -> None:
    dispatcher = RuntimeDispatcher(
        max_queue_size=10,
        worker_count=2,
    )

    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def operation():
        nonlocal active, peak

        async with lock:
            active += 1
            peak = max(peak, active)

        await asyncio.sleep(0.02)

        async with lock:
            active -= 1

    await dispatcher.start()

    for _ in range(4):
        await dispatcher.submit(operation)

    await dispatcher.wait()
    await dispatcher.stop()

    state = await dispatcher.state()

    assert state.processed == 4
    assert peak >= 2


@pytest.mark.asyncio
async def test_dispatcher_tracks_failed_operations() -> None:
    dispatcher = RuntimeDispatcher(
        max_queue_size=10,
        worker_count=2,
    )

    async def operation():
        raise RuntimeError("dispatch failure")

    await dispatcher.start()
    await dispatcher.submit(operation)

    await asyncio.sleep(0.05)

    state = await dispatcher.state()

    assert state.failed == 1
    assert state.processed == 0

    await dispatcher.stop()


@pytest.mark.asyncio
async def test_dispatcher_handles_multiple_start_stop_calls() -> None:
    dispatcher = RuntimeDispatcher(
        max_queue_size=10,
        worker_count=1,
    )

    await dispatcher.start()
    await dispatcher.start()

    state = await dispatcher.state()

    assert state.running is True

    await dispatcher.stop()
    await dispatcher.stop()

    state = await dispatcher.state()

    assert state.running is False


def test_dispatcher_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        RuntimeDispatcher(max_queue_size=0)

    with pytest.raises(ValueError):
        RuntimeDispatcher(worker_count=0)
