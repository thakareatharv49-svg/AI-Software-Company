
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RecoveryState(StrEnum):
    HEALTHY = "healthy"
    FAILED = "failed"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    EXHAUSTED = "exhausted"


@dataclass
class RecoveryRecord:
    run_id: str
    state: RecoveryState = RecoveryState.HEALTHY
    attempts: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeFailureRecovery:
    def __init__(self, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self.max_attempts = max_attempts
        self._records: dict[str, RecoveryRecord] = {}

    def register(self, run_id: str) -> RecoveryRecord:
        record = RecoveryRecord(
            run_id=run_id,
            max_attempts=self.max_attempts,
        )
        self._records[run_id] = record
        return record

    def get(self, run_id: str) -> RecoveryRecord:
        if run_id not in self._records:
            raise KeyError(run_id)
        return self._records[run_id]

    def mark_failed(
        self,
        run_id: str,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> RecoveryRecord:
        record = self.get(run_id)
        record.state = RecoveryState.FAILED
        record.last_error = error

        if metadata:
            record.metadata.update(metadata)

        return record

    def begin_recovery(self, run_id: str) -> RecoveryRecord:
        record = self.get(run_id)

        if record.attempts >= record.max_attempts:
            record.state = RecoveryState.EXHAUSTED
            return record

        record.attempts += 1
        record.state = RecoveryState.RECOVERING
        return record

    def mark_recovered(
        self,
        run_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> RecoveryRecord:
        record = self.get(run_id)
        record.state = RecoveryState.RECOVERED
        record.last_error = None

        if metadata:
            record.metadata.update(metadata)

        return record

    def exhaust(self, run_id: str) -> RecoveryRecord:
        record = self.get(run_id)
        record.state = RecoveryState.EXHAUSTED
        return record

    def can_retry(self, run_id: str) -> bool:
        record = self.get(run_id)

        if record.state in (
            RecoveryState.EXHAUSTED,
            RecoveryState.RECOVERED,
        ):
            return False

        return record.attempts < record.max_attempts

    def records(self) -> list[RecoveryRecord]:
        return list(self._records.values())




