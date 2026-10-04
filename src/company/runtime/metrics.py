from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeMetrics:
    total_started: int
    total_completed: int
    total_failed: int
    active_tasks: int


class RuntimeMetricsCollector:
    def __init__(self) -> None:
        self._total_started = 0
        self._total_completed = 0
        self._total_failed = 0
        self._active_tasks = 0
        self._lock = asyncio.Lock()

    async def started(self) -> None:
        async with self._lock:
            self._total_started += 1
            self._active_tasks += 1

    async def completed(self) -> None:
        async with self._lock:
            self._total_completed += 1
            self._active_tasks = max(0, self._active_tasks - 1)

    async def failed(self) -> None:
        async with self._lock:
            self._total_failed += 1
            self._active_tasks = max(0, self._active_tasks - 1)

    async def snapshot(self) -> RuntimeMetrics:
        async with self._lock:
            return RuntimeMetrics(
                total_started=self._total_started,
                total_completed=self._total_completed,
                total_failed=self._total_failed,
                active_tasks=self._active_tasks,
            )


class InstrumentedRuntimeExecutor:
    def __init__(
        self,
        operation: Callable[[], Awaitable[object]],
        metrics: RuntimeMetricsCollector,
    ) -> None:
        self.operation = operation
        self.metrics = metrics

    async def execute(self) -> object:
        await self.metrics.started()

        try:
            result = await self.operation()
        except asyncio.CancelledError:
            await self.metrics.failed()
            raise
        except Exception:
            await self.metrics.failed()
            raise
        else:
            await self.metrics.completed()
            return result
