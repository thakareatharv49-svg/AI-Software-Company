from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeHeartbeat:
    timestamp: float
    healthy: bool


class RuntimeHeartbeatMonitor:
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
        self._last_heartbeat: RuntimeHeartbeat | None = None

    async def check(self) -> RuntimeHeartbeat:
        healthy = await self.health_check()

        heartbeat = RuntimeHeartbeat(
            timestamp=asyncio.get_running_loop().time(),
            healthy=healthy,
        )

        self._last_heartbeat = heartbeat
        return heartbeat

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        async def loop() -> None:
            while True:
                await self.check()
                await asyncio.sleep(self.interval_seconds)

        self._task = asyncio.create_task(loop())

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    @property
    def last_heartbeat(self) -> RuntimeHeartbeat | None:
        return self._last_heartbeat

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()
