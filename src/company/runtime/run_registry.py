from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4


class RuntimeRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class RuntimeRun:
    run_id: str
    status: RuntimeRunStatus
    result: Any = None
    error: BaseException | None = None


class RuntimeRunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, RuntimeRun] = {}

    def create(self) -> RuntimeRun:
        run = RuntimeRun(
            run_id=str(uuid4()),
            status=RuntimeRunStatus.QUEUED,
        )
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> RuntimeRun | None:
        return self._runs.get(run_id)

    def mark_running(self, run_id: str) -> RuntimeRun:
        run = self._require(run_id)
        run.status = RuntimeRunStatus.RUNNING
        return run

    def mark_completed(self, run_id: str, result: Any) -> RuntimeRun:
        run = self._require(run_id)
        run.status = RuntimeRunStatus.COMPLETED
        run.result = result
        run.error = None
        return run

    def mark_failed(self, run_id: str, error: BaseException) -> RuntimeRun:
        run = self._require(run_id)
        run.status = RuntimeRunStatus.FAILED
        run.error = error
        return run

    def mark_cancelled(self, run_id: str) -> RuntimeRun:
        run = self._require(run_id)
        run.status = RuntimeRunStatus.CANCELLED
        return run

    def all(self) -> tuple[RuntimeRun, ...]:
        return tuple(self._runs.values())

    def _require(self, run_id: str) -> RuntimeRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"Unknown runtime run: {run_id}")
        return run
