from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeTimeoutResult:
    completed: bool
    timed_out: bool
    duration_seconds: float


class RuntimeTimeoutController:
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")

        self.timeout_seconds = timeout_seconds

    async def execute(self, operation) -> RuntimeTimeoutResult:
        loop = asyncio.get_running_loop()
        started = loop.time()

        try:
            await asyncio.wait_for(
                operation(),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            duration = loop.time() - started
            return RuntimeTimeoutResult(
                completed=False,
                timed_out=True,
                duration_seconds=duration,
            )

        duration = loop.time() - started
        return RuntimeTimeoutResult(
            completed=True,
            timed_out=False,
            duration_seconds=duration,
        )
