from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AutonomousExecutionStatus(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True, frozen=True)
class AutonomousExecutionResult:
    run_id: str
    status: AutonomousExecutionStatus
    result: Any = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == AutonomousExecutionStatus.COMPLETED
