from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True, frozen=True)
class AuditRecord:
    record_id: str
    run_id: str
    event_type: str
    timestamp: str
    project_id: str | None
    payload: dict[str, Any]


class ObservabilityService:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []
        self._run_metrics: dict[str, dict[str, int]] = {}

    def create_run_id(self) -> str:
        return str(uuid4())

    def record(
        self,
        *,
        run_id: str,
        event_type: str,
        project_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditRecord:
        record = AuditRecord(
            record_id=str(uuid4()),
            run_id=run_id,
            event_type=event_type,
            timestamp=datetime.now(UTC).isoformat(),
            project_id=project_id,
            payload=dict(payload or {}),
        )

        self._records.append(record)

        metrics = self._run_metrics.setdefault(
            run_id,
            {
                "events": 0,
                "failures": 0,
                "recoveries": 0,
                "completed": 0,
            },
        )

        metrics["events"] += 1

        if event_type == "autonomous.run.failed":
            metrics["failures"] += 1

        if event_type == "autonomous.run.recovery_available":
            metrics["recoveries"] += 1

        if event_type == "autonomous.run.completed":
            metrics["completed"] += 1

        return record

    def records(self, run_id: str | None = None) -> list[AuditRecord]:
        if run_id is None:
            return list(self._records)

        return [
            record
            for record in self._records
            if record.run_id == run_id
        ]

    def metrics(self, run_id: str) -> dict[str, int]:
        return dict(
            self._run_metrics.get(
                run_id,
                {
                    "events": 0,
                    "failures": 0,
                    "recoveries": 0,
                    "completed": 0,
                },
            )
        )

    def export(self, run_id: str | None = None) -> list[dict[str, Any]]:
        return [asdict(record) for record in self.records(run_id)]

    def clear(self) -> None:
        self._records.clear()
        self._run_metrics.clear()
