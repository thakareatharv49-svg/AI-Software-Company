from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeCancellationResult:
    cancelled: bool
    completed: bool


class RuntimeCancellationController:
    def __init__(self) -> None:
        self._cancelled = False
        self._lock = asyncio.Lock()

    async def cancel(self) -> None:
        async with self._lock:
            self._cancelled = True

    async def reset(self) -> None:
        async with self._lock:
            self._cancelled = False

    async def is_cancelled(self) -> bool:
        async with self._lock:
            return self._cancelled

    async def execute(self, operation) -> RuntimeCancellationResult:
        if await self.is_cancelled():
            return RuntimeCancellationResult(
                cancelled=True,
                completed=False,
            )

        task = asyncio.create_task(operation())

        while not task.done():
            if await self.is_cancelled():
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass

                return RuntimeCancellationResult(
                    cancelled=True,
                    completed=False,
                )

            await asyncio.sleep(0)

        await task

        return RuntimeCancellationResult(
            cancelled=False,
            completed=True,
        )
