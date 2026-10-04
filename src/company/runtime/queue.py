from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeQueueState:
    size: int
    max_size: int
    full: bool
    empty: bool


class RuntimeQueueFullError(RuntimeError):
    pass


class RuntimeWorkQueue:
    def __init__(self, max_size: int = 100) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")

        self.max_size = max_size
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)

    async def submit(self, operation) -> None:
        if self._queue.full():
            raise RuntimeQueueFullError("runtime work queue is full")

        await self._queue.put(operation)

    async def get(self):
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    async def state(self) -> RuntimeQueueState:
        size = self._queue.qsize()

        return RuntimeQueueState(
            size=size,
            max_size=self.max_size,
            full=self._queue.full(),
            empty=self._queue.empty(),
        )

    async def clear(self) -> int:
        removed = 0

        while True:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            else:
                self._queue.task_done()
                removed += 1

        return removed


class RuntimeQueueWorker:
    def __init__(self, queue: RuntimeWorkQueue) -> None:
        self.queue = queue
        self._running = False

    async def run_once(self) -> None:
        operation = await self.queue.get()

        try:
            await operation()
        finally:
            self.queue.task_done()

    async def run(self) -> None:
        self._running = True

        try:
            while self._running:
                await self.run_once()
        except asyncio.CancelledError:
            self._running = False
            raise

    async def stop(self) -> None:
        self._running = False

    @property
    def running(self) -> bool:
        return self._running
