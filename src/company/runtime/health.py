from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeHealth:
    healthy: bool
    running: bool
    active_tasks: int
    max_concurrent_runs: int


class RuntimeHealthMonitor:
    def __init__(
        self,
        *,
        max_concurrent_runs: int,
        is_running: Callable[[], bool],
        active_tasks: Callable[[], Awaitable[int]],
    ) -> None:
        if max_concurrent_runs < 1:
            raise ValueError("max_concurrent_runs must be at least 1")

        self.max_concurrent_runs = max_concurrent_runs
        self._is_running = is_running
        self._active_tasks = active_tasks
        self._last_health: RuntimeHealth | None = None

    async def check(self) -> RuntimeHealth:
        running = self._is_running()
        active_tasks = await self._active_tasks()

        healthy = (
            running
            and active_tasks >= 0
            and active_tasks <= self.max_concurrent_runs
        )

        health = RuntimeHealth(
            healthy=healthy,
            running=running,
            active_tasks=active_tasks,
            max_concurrent_runs=self.max_concurrent_runs,
        )

        self._last_health = health
        return health

    @property
    def last_health(self) -> RuntimeHealth | None:
        return self._last_health
