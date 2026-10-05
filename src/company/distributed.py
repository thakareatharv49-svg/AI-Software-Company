from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, TypeVar
from uuid import uuid4

T = TypeVar("T")


class WorkerStatus(StrEnum):
    READY = "ready"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass(frozen=True)
class WorkItem:
    id: str
    payload: object
    attempt: int = 0


@dataclass(frozen=True)
class WorkResult:
    work_id: str
    worker_id: str
    success: bool
    value: object = None
    error: str | None = None


@dataclass
class Worker:
    id: str
    status: WorkerStatus = WorkerStatus.READY
    completed: int = 0
    failed: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.status, WorkerStatus):
            self.status = WorkerStatus(self.status)


class DistributedExecutor:
    def __init__(
        self,
        workers: tuple[Worker, ...] | None = None,
        max_attempts: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.workers = list(workers or ())
        self.max_attempts = max_attempts
        self._cursor = 0
        self.results: list[WorkResult] = []

    def register(self, worker: Worker) -> None:
        if any(item.id == worker.id for item in self.workers):
            raise ValueError("worker already registered")
        self.workers.append(worker)

    def submit(self, payload: object) -> WorkItem:
        return WorkItem(str(uuid4()), payload)

    def execute(
        self,
        item: WorkItem,
        handler: Callable[[object], T],
    ) -> WorkResult:
        ready = [worker for worker in self.workers if worker.status == WorkerStatus.READY]
        if not ready:
            raise RuntimeError("no ready workers")
        worker = ready[self._cursor % len(ready)]
        self._cursor += 1
        worker.status = WorkerStatus.BUSY
        try:
            value = handler(item.payload)
            worker.completed += 1
            result = WorkResult(item.id, worker.id, True, value)
        except Exception as exc:
            worker.failed += 1
            result = WorkResult(item.id, worker.id, False, error=str(exc))
        finally:
            worker.status = WorkerStatus.READY
        self.results.append(result)
        return result

    def execute_with_retry(
        self,
        item: WorkItem,
        handler: Callable[[object], T],
    ) -> WorkResult:
        last: WorkResult | None = None
        for attempt in range(self.max_attempts):
            result = self.execute(WorkItem(item.id, item.payload, attempt), handler)
            last = result
            if result.success:
                return result
        assert last is not None
        return last

    def health(self) -> dict[str, int]:
        return {
            status.value: sum(worker.status == status for worker in self.workers)
            for status in WorkerStatus
        }
