from __future__ import annotations

import asyncio

import pytest

from company.runtime.queue import (
    RuntimeQueueFullError,
    RuntimeQueueWorker,
    RuntimeWorkQueue,
)


@pytest.mark.asyncio
async def test_queue_accepts_work() -> None:
    queue = RuntimeWorkQueue(max_size=2)

    async def operation():
        return None

    await queue.submit(operation)

    state = await queue.state()

    assert state.size == 1
    assert state.max_size == 2
    assert state.full is False
    assert state.empty is False


@pytest.mark.asyncio
async def test_queue_rejects_when_full() -> None:
    queue = RuntimeWorkQueue(max_size=1)

    async def operation():
        return None

    await queue.submit(operation)

    with pytest.raises(RuntimeQueueFullError, match="queue is full"):
        await queue.submit(operation)

    state = await queue.state()

    assert state.size == 1
    assert state.full is True


@pytest.mark.asyncio
async def test_worker_executes_queued_operation() -> None:
    queue = RuntimeWorkQueue(max_size=2)
    worker = RuntimeQueueWorker(queue)
    completed = asyncio.Event()

    async def operation():
        completed.set()

    await queue.submit(operation)

    await worker.run_once()
    await queue.join()

    assert completed.is_set()

    state = await queue.state()

    assert state.size == 0
    assert state.empty is True


@pytest.mark.asyncio
async def test_worker_marks_work_done_after_failure() -> None:
    queue = RuntimeWorkQueue(max_size=1)
    worker = RuntimeQueueWorker(queue)

    async def operation():
        raise RuntimeError("worker failure")

    await queue.submit(operation)

    with pytest.raises(RuntimeError, match="worker failure"):
        await worker.run_once()

    await queue.join()

    state = await queue.state()

    assert state.empty is True


@pytest.mark.asyncio
async def test_queue_clear_removes_pending_work() -> None:
    queue = RuntimeWorkQueue(max_size=3)

    async def operation():
        return None

    await queue.submit(operation)
    await queue.submit(operation)

    removed = await queue.clear()

    assert removed == 2

    state = await queue.state()

    assert state.size == 0
    assert state.empty is True


@pytest.mark.asyncio
async def test_queue_get_and_task_done() -> None:
    queue = RuntimeWorkQueue(max_size=1)
    called = False

    async def operation():
        nonlocal called
        called = True

    await queue.submit(operation)

    retrieved = await queue.get()

    assert retrieved is operation

    await retrieved()
    queue.task_done()
    await queue.join()

    assert called is True


@pytest.mark.asyncio
async def test_worker_can_stop() -> None:
    queue = RuntimeWorkQueue(max_size=1)
    worker = RuntimeQueueWorker(queue)

    task = asyncio.create_task(worker.run())

    await asyncio.sleep(0)
    assert worker.running is True

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert worker.running is False


def test_invalid_queue_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        RuntimeWorkQueue(max_size=0)
