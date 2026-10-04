from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeSupervisorStatus:
    running: bool
    healthy: bool
    restart_count: int


class RuntimeSupervisor:
    def __init__(
        self,
        health_check: Callable[[], Awaitable[bool]],
        interval_seconds: float = 30.0,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than 0")

        self.health_check = health_check
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._healthy = False
        self._restart_count = 0

    async def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor())

    async def _monitor(self) -> None:
        while self._running:
            try:
                self._healthy = await self.health_check()
            except Exception:
                self._healthy = False

            if not self._healthy and self._running:
                self._restart_count += 1

            await asyncio.sleep(self.interval_seconds)

    async def stop(self) -> None:
        self._running = False

        if self._task is None:
            return

        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def check_now(self) -> bool:
        try:
            self._healthy = await self.health_check()
        except Exception:
            self._healthy = False

        return self._healthy

    def status(self) -> RuntimeSupervisorStatus:
        return RuntimeSupervisorStatus(
            running=self._running,
            healthy=self._healthy,
            restart_count=self._restart_count,
        )
