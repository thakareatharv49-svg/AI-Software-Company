from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeWorkerPoolState:
    running: bool
    worker_count: int
    processed: int
    failed: int


class RuntimeWorkerPool:
    def __init__(self, worker, worker_count: int = 1) -> None:
        if worker_count < 1:
            raise ValueError("worker_count must be >= 1")

        self.queue = worker.queue
        self.worker_count = worker_count
        self._worker_type = type(worker)
        self._workers = [worker]
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        self._workers = [
            self._worker_type(self.queue)
            for _ in range(self.worker_count)
        ]

        self._running = True
        self._tasks = [
            asyncio.create_task(worker.run())
            for worker in self._workers
        ]

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False

        for worker in self._workers:
            await worker.stop()

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks = []

    async def state(self) -> RuntimeWorkerPoolState:
        states = [await worker.state() for worker in self._workers]

        return RuntimeWorkerPoolState(
            running=self._running,
            worker_count=self.worker_count,
            processed=sum(state.processed for state in states),
            failed=sum(state.failed for state in states),
        )
