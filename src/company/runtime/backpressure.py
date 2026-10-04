from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeBackpressure:
    allowed: bool
    active_tasks: int
    max_tasks: int


class RuntimeBackpressureController:
    def __init__(self, max_tasks: int = 1) -> None:
        if max_tasks < 1:
            raise ValueError("max_tasks must be >= 1")

        self.max_tasks = max_tasks
        self._active_tasks = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> RuntimeBackpressure:
        async with self._lock:
            if self._active_tasks >= self.max_tasks:
                return RuntimeBackpressure(
                    allowed=False,
                    active_tasks=self._active_tasks,
                    max_tasks=self.max_tasks,
                )

            self._active_tasks += 1

            return RuntimeBackpressure(
                allowed=True,
                active_tasks=self._active_tasks,
                max_tasks=self.max_tasks,
            )

    async def release(self) -> RuntimeBackpressure:
        async with self._lock:
            if self._active_tasks > 0:
                self._active_tasks -= 1

            return RuntimeBackpressure(
                allowed=True,
                active_tasks=self._active_tasks,
                max_tasks=self.max_tasks,
            )

    async def status(self) -> RuntimeBackpressure:
        async with self._lock:
            return RuntimeBackpressure(
                allowed=self._active_tasks < self.max_tasks,
                active_tasks=self._active_tasks,
                max_tasks=self.max_tasks,
            )


class BackpressuredRuntimeExecutor:
    def __init__(
        self,
        operation: Callable[[], Awaitable[object]],
        controller: RuntimeBackpressureController,
    ) -> None:
        self.operation = operation
        self.controller = controller

    async def execute(self) -> object:
        state = await self.controller.acquire()

        if not state.allowed:
            raise RuntimeError("runtime capacity exceeded")

        try:
            return await self.operation()
        finally:
            await self.controller.release()
