from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeWorkerState:
    running: bool
    processed: int
    failed: int


class RuntimeWorker:
    def __init__(self, queue) -> None:
        self.queue = queue
        self._running = False
        self._processed = 0
        self._failed = 0

    async def process_once(self) -> None:
        operation = await self.queue.get()

        try:
            await operation()
            self._processed += 1
        except Exception:
            self._failed += 1
            raise
        finally:
            self.queue.task_done()

    async def run(self) -> None:
        if self._running:
            return

        self._running = True

        try:
            while self._running:
                await self.process_once()
        except asyncio.CancelledError:
            raise
        finally:
            self._running = False

    async def stop(self) -> None:
        self._running = False

    async def state(self) -> RuntimeWorkerState:
        return RuntimeWorkerState(
            running=self._running,
            processed=self._processed,
            failed=self._failed,
        )
