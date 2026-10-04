from __future__ import annotations

from dataclasses import dataclass

from company.runtime.queue import RuntimeWorkQueue
from company.runtime.worker import RuntimeWorker
from company.runtime.worker_pool import RuntimeWorkerPool


@dataclass(slots=True, frozen=True)
class RuntimeDispatcherState:
    running: bool
    queued: int
    processed: int
    failed: int
    worker_count: int


class RuntimeDispatcher:
    def __init__(
        self,
        max_queue_size: int = 100,
        worker_count: int = 1,
    ) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be >= 1")
        if worker_count < 1:
            raise ValueError("worker_count must be >= 1")

        self.queue = RuntimeWorkQueue(max_size=max_queue_size)
        self.worker = RuntimeWorker(self.queue)
        self.pool = RuntimeWorkerPool(
            self.worker,
            worker_count=worker_count,
        )

    async def start(self) -> None:
        await self.pool.start()

    async def submit(self, operation) -> None:
        await self.queue.submit(operation)

    async def wait(self) -> None:
        await self.queue.join()

    async def stop(self) -> None:
        await self.pool.stop()

    async def state(self) -> RuntimeDispatcherState:
        pool_state = await self.pool.state()
        queue_state = await self.queue.state()

        return RuntimeDispatcherState(
            running=pool_state.running,
            queued=queue_state.size,
            processed=pool_state.processed,
            failed=pool_state.failed,
            worker_count=pool_state.worker_count,
        )
