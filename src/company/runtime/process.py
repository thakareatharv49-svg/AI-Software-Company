from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum


class RuntimeProcessStatus(StrEnum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(slots=True, frozen=True)
class RuntimeProcessState:
    status: RuntimeProcessStatus
    running: bool
    return_code: int | None
    error: str | None


class RuntimeProcessController:
    def __init__(
        self,
        target: Callable[[], Awaitable[None]],
    ) -> None:
        if not callable(target):
            raise TypeError("target must be callable")

        self._target = target
        self._task: asyncio.Task[None] | None = None
        self._status = RuntimeProcessStatus.CREATED
        self._return_code: int | None = None
        self._error: str | None = None

    async def start(self) -> None:
        if self._status in {
            RuntimeProcessStatus.STARTING,
            RuntimeProcessStatus.RUNNING,
        }:
            return

        if self._status is RuntimeProcessStatus.STOPPING:
            raise RuntimeError("Runtime process is stopping.")

        self._status = RuntimeProcessStatus.STARTING
        self._return_code = None
        self._error = None

        self._task = asyncio.create_task(self._run())

        await asyncio.sleep(0)

        if (
            self._status is RuntimeProcessStatus.STARTING
            and self._task is not None
            and not self._task.done()
        ):
            self._status = RuntimeProcessStatus.RUNNING

    async def _run(self) -> None:
        try:
            await self._target()

            if self._status is not RuntimeProcessStatus.STOPPING:
                self._return_code = 0
                self._status = RuntimeProcessStatus.STOPPED
        except asyncio.CancelledError:
            self._return_code = -1
            self._status = RuntimeProcessStatus.STOPPED
            raise
        except Exception as exc:
            self._return_code = 1
            self._error = str(exc)
            self._status = RuntimeProcessStatus.FAILED

    async def wait(self) -> None:
        if self._task is None:
            return

        await asyncio.gather(
            self._task,
            return_exceptions=True,
        )

    async def stop(self) -> None:
        if self._task is None:
            self._status = RuntimeProcessStatus.STOPPED
            return

        if self._task.done():
            await self.wait()
            return

        self._status = RuntimeProcessStatus.STOPPING
        self._task.cancel()

        await asyncio.gather(
            self._task,
            return_exceptions=True,
        )

        self._status = RuntimeProcessStatus.STOPPED

    async def state(self) -> RuntimeProcessState:
        running = (
            self._task is not None
            and not self._task.done()
            and self._status is RuntimeProcessStatus.RUNNING
        )

        return RuntimeProcessState(
            status=self._status,
            running=running,
            return_code=self._return_code,
            error=self._error,
        )
