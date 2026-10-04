from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeShutdownState:
    requested: bool
    completed: bool
    active_tasks: int


class RuntimeShutdownController:
    def __init__(
        self,
        active_tasks: Callable[[], Awaitable[int]],
    ) -> None:
        self._active_tasks = active_tasks
        self._shutdown_requested = False
        self._shutdown_completed = False
        self._event = asyncio.Event()

    async def request_shutdown(self) -> RuntimeShutdownState:
        self._shutdown_requested = True
        self._event.set()

        active_tasks = await self._active_tasks()

        if active_tasks == 0:
            self._shutdown_completed = True

        return RuntimeShutdownState(
            requested=self._shutdown_requested,
            completed=self._shutdown_completed,
            active_tasks=active_tasks,
        )

    async def wait_for_request(self) -> None:
        await self._event.wait()

    async def complete(self) -> RuntimeShutdownState:
        self._shutdown_requested = True
        self._shutdown_completed = True
        self._event.set()

        active_tasks = await self._active_tasks()

        return RuntimeShutdownState(
            requested=True,
            completed=True,
            active_tasks=active_tasks,
        )

    async def wait_until_complete(self) -> None:
        while not self._shutdown_completed:
            await asyncio.sleep(0)

    async def status(self) -> RuntimeShutdownState:
        active_tasks = await self._active_tasks()

        return RuntimeShutdownState(
            requested=self._shutdown_requested,
            completed=self._shutdown_completed,
            active_tasks=active_tasks,
        )
