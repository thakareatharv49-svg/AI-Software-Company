from __future__ import annotations

import asyncio

import pytest

from company.runtime.queue import RuntimeWorkQueue
from company.runtime.worker import RuntimeWorker


@pytest.mark.asyncio
async def test_worker_processes_queued_operation() -> None:
    queue = RuntimeWorkQueue(max_size=2)
    worker = RuntimeWorker(queue)
    completed = asyncio.Event()

    async def operation():
        completed.set()

    await queue.submit(operation)

    await worker.process_once()

    state = await worker.state()

    assert completed.is_set()
    assert state.running is False
    assert state.processed == 1
    assert state.failed == 0


@pytest.mark.asyncio
async def test_worker_records_failed_operation() -> None:
    queue = RuntimeWorkQueue(max_size=2)
    worker = RuntimeWorker(queue)

    async def operation():
        raise RuntimeError("worker failure")

    await queue.submit(operation)

    with pytest.raises(RuntimeError, match="worker failure"):
        await worker.process_once()

    state = await worker.state()

    assert state.processed == 0
    assert state.failed == 1


@pytest.mark.asyncio
async def test_worker_run_processes_multiple_operations() -> None:
    queue = RuntimeWorkQueue(max_size=3)
    worker = RuntimeWorker(queue)
    completed = 0

    async def operation():
        nonlocal completed
        completed += 1

        if completed == 3:
            await worker.stop()

    for _ in range(3):
        await queue.submit(operation)

    await worker.run()
    await queue.join()

    state = await worker.state()

    assert completed == 3
    assert state.processed == 3
    assert state.failed == 0
    assert state.running is False


@pytest.mark.asyncio
async def test_worker_stop_sets_running_false() -> None:
    queue = RuntimeWorkQueue(max_size=1)
    worker = RuntimeWorker(queue)

    task = asyncio.create_task(worker.run())

    await asyncio.sleep(0)

    assert (await worker.state()).running is True

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    await worker.stop()

    assert (await worker.state()).running is False


@pytest.mark.asyncio
async def test_worker_restarts_after_stop() -> None:
    queue = RuntimeWorkQueue(max_size=2)
    worker = RuntimeWorker(queue)
    completed = asyncio.Event()

    async def operation():
        completed.set()
        await worker.stop()

    await queue.submit(operation)

    await worker.run()
    await queue.join()

    assert completed.is_set()

    state = await worker.state()

    assert state.processed == 1
    assert state.running is False
