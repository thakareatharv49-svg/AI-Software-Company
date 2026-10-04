from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeShutdownResult:
    stopped: bool
    cancelled_tasks: int


class RuntimeLifecycle:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[object]] = set()
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            self._running = True

    async def register_task(self, task: asyncio.Task[object]) -> None:
        async with self._lock:
            if not self._running:
                raise RuntimeError("runtime lifecycle is not running")

            self._tasks.add(task)

        task.add_done_callback(self._remove_task)

    def _remove_task(self, task: asyncio.Task[object]) -> None:
        self._tasks.discard(task)

    async def active_tasks(self) -> int:
        async with self._lock:
            return len(self._tasks)

    async def stop(
        self,
        timeout_seconds: float = 30.0,
    ) -> RuntimeShutdownResult:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")

        async with self._lock:
            self._running = False
            tasks = list(self._tasks)

        for task in tasks:
            if not task.done():
                task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        async with self._lock:
            self._tasks.clear()

        return RuntimeShutdownResult(
            stopped=True,
            cancelled_tasks=sum(
                1 for task in tasks if task.cancelled()
            ),
        )

    @property
    def running(self) -> bool:
        return self._running
