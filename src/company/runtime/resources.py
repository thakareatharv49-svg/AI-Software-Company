from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeResourceState:
    active_tasks: int
    max_tasks: int
    utilization_percent: float
    available_capacity: int


class RuntimeResourceMonitor:
    def __init__(self, max_tasks: int = 1) -> None:
        if max_tasks < 1:
            raise ValueError("max_tasks must be >= 1")

        self.max_tasks = max_tasks
        self._active_tasks = 0
        self._lock = asyncio.Lock()

    async def set_active_tasks(self, active_tasks: int) -> RuntimeResourceState:
        if active_tasks < 0:
            raise ValueError("active_tasks must be >= 0")

        async with self._lock:
            self._active_tasks = active_tasks
            return self._state()

    async def increment(self) -> RuntimeResourceState:
        async with self._lock:
            if self._active_tasks < self.max_tasks:
                self._active_tasks += 1
            return self._state()

    async def decrement(self) -> RuntimeResourceState:
        async with self._lock:
            if self._active_tasks > 0:
                self._active_tasks -= 1
            return self._state()

    async def snapshot(self) -> RuntimeResourceState:
        async with self._lock:
            return self._state()

    def _state(self) -> RuntimeResourceState:
        utilization = (self._active_tasks / self.max_tasks) * 100

        return RuntimeResourceState(
            active_tasks=self._active_tasks,
            max_tasks=self.max_tasks,
            utilization_percent=utilization,
            available_capacity=max(self.max_tasks - self._active_tasks, 0),
        )
