from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeStatus:
    running: bool
    active_runs: int
    max_concurrent_runs: int


class RuntimeCoordinator:
    def __init__(self, max_concurrent_runs: int = 1) -> None:
        if max_concurrent_runs < 1:
            raise ValueError("max_concurrent_runs must be at least 1")

        self.max_concurrent_runs = max_concurrent_runs
        self._semaphore = asyncio.Semaphore(max_concurrent_runs)
        self._active_runs = 0
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            self._running = True

    async def stop(self) -> None:
        async with self._lock:
            self._running = False

    async def status(self) -> RuntimeStatus:
        async with self._lock:
            return RuntimeStatus(
                running=self._running,
                active_runs=self._active_runs,
                max_concurrent_runs=self.max_concurrent_runs,
            )

    async def execute(
        self,
        operation: Callable[[], Awaitable[object]],
    ) -> object:
        async with self._lock:
            if not self._running:
                raise RuntimeError("runtime coordinator is not running")

        async with self._semaphore:
            async with self._lock:
                self._active_runs += 1

            try:
                return await operation()
            finally:
                async with self._lock:
                    self._active_runs -= 1
