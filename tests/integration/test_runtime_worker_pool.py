from __future__ import annotations

import asyncio

import pytest

from company.runtime.queue import RuntimeWorkQueue
from company.runtime.worker import RuntimeWorker
from company.runtime.worker_pool import RuntimeWorkerPool


@pytest.mark.asyncio
async def test_worker_pool_starts_workers() -> None:
    queue = RuntimeWorkQueue(max_size=10)
    worker = RuntimeWorker(queue)
    pool = RuntimeWorkerPool(worker, worker_count=2)

    await pool.start()
    await asyncio.sleep(0)

    state = await pool.state()

    assert state.running is True
    assert state.worker_count == 2

    await pool.stop()

    state = await pool.state()

    assert state.running is False


@pytest.mark.asyncio
async def test_worker_pool_processes_work() -> None:
    queue = RuntimeWorkQueue(max_size=10)
    worker = RuntimeWorker(queue)
    pool = RuntimeWorkerPool(worker, worker_count=2)

    completed = 0
    lock = asyncio.Lock()

    async def operation():
        nonlocal completed
        await asyncio.sleep(0)
        async with lock:
            completed += 1

    await pool.start()

    for _ in range(4):
        await queue.submit(operation)

    await queue.join()
    await pool.stop()

    state = await pool.state()

    assert completed == 4
    assert state.processed == 4
    assert state.failed == 0


@pytest.mark.asyncio
async def test_worker_pool_uses_multiple_workers_concurrently() -> None:
    queue = RuntimeWorkQueue(max_size=10)
    worker = RuntimeWorker(queue)
    pool = RuntimeWorkerPool(worker, worker_count=2)

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

    await pool.start()

    for _ in range(4):
        await queue.submit(operation)

    await queue.join()
    await pool.stop()

    state = await pool.state()

    assert state.processed == 4
    assert peak >= 2


@pytest.mark.asyncio
async def test_worker_pool_records_failures() -> None:
    queue = RuntimeWorkQueue(max_size=10)
    worker = RuntimeWorker(queue)
    pool = RuntimeWorkerPool(worker, worker_count=2)

    async def operation():
        raise RuntimeError("failure")

    await pool.start()
    await queue.submit(operation)

    await asyncio.sleep(0.05)

    state = await pool.state()

    assert state.failed == 1
    assert state.processed == 0

    await pool.stop()


@pytest.mark.asyncio
async def test_worker_pool_stop_is_idempotent() -> None:
    queue = RuntimeWorkQueue(max_size=2)
    worker = RuntimeWorker(queue)
    pool = RuntimeWorkerPool(worker, worker_count=1)

    await pool.start()
    await pool.stop()
    await pool.stop()

    state = await pool.state()

    assert state.running is False


def test_invalid_worker_count_is_rejected() -> None:
    queue = RuntimeWorkQueue(max_size=1)
    worker = RuntimeWorker(queue)

    with pytest.raises(ValueError):
        RuntimeWorkerPool(worker, worker_count=0)
