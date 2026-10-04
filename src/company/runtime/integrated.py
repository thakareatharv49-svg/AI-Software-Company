from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from .dispatcher import RuntimeDispatcher

T = TypeVar("T")


@dataclass(slots=True, frozen=True)
class RuntimeExecutionState:
    running: bool
    queued: int
    processed: int
    failed: int
    worker_count: int


class IntegratedProductionRuntime:
    """
    Production execution facade built on the existing runtime dispatcher.

    The dispatcher remains responsible for worker lifecycle, queueing,
    concurrency and execution accounting. This class provides the stable
    production-facing API without duplicating those responsibilities.
    """

    def __init__(
        self,
        *,
        max_queue_size: int = 100,
        worker_count: int = 1,
        dispatcher: RuntimeDispatcher | None = None,
    ) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be at least 1")

        if worker_count < 1:
            raise ValueError("worker_count must be at least 1")

        self.dispatcher = dispatcher or RuntimeDispatcher(
            max_queue_size=max_queue_size,
            worker_count=worker_count,
        )

    async def start(self) -> None:
        await self.dispatcher.start()

    async def submit(
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> None:
        state = await self.dispatcher.state()

        if not state.running:
            raise RuntimeError(
                "Integrated production runtime is not running."
            )

        await self.dispatcher.submit(operation)

    async def wait(self) -> None:
        await self.dispatcher.wait()

    async def stop(self) -> None:
        await self.dispatcher.stop()

    async def state(self) -> RuntimeExecutionState:
        state = await self.dispatcher.state()

        return RuntimeExecutionState(
            running=state.running,
            queued=state.queued,
            processed=state.processed,
            failed=state.failed,
            worker_count=state.worker_count,
        )
