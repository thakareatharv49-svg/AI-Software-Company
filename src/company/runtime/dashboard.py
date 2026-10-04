
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .observability import RuntimeObservability


@dataclass(frozen=True)
class RuntimeDashboardSnapshot:
    status: str
    events: int
    runs: int
    completed: int
    failed: int
    average_duration_seconds: float


class RuntimeDashboard:
    def __init__(
        self,
        observability: RuntimeObservability,
    ) -> None:
        self.observability = observability

    def snapshot(self, status: str = "running") -> RuntimeDashboardSnapshot:
        events = self.observability.events()

        run_ids = {
            event.run_id
            for event in events
            if event.run_id is not None
        }

        completed = sum(
            1
            for event in events
            if event.status == "completed"
        )

        failed = sum(
            1
            for event in events
            if event.status == "failed"
        )

        durations = [
            event.duration_seconds
            for event in events
            if event.duration_seconds is not None
        ]

        return RuntimeDashboardSnapshot(
            status=status,
            events=len(events),
            runs=len(run_ids),
            completed=completed,
            failed=failed,
            average_duration_seconds=(
                sum(durations) / len(durations)
                if durations
                else 0.0
            ),
        )

    def as_dict(self, status: str = "running") -> dict[str, Any]:
        snapshot = self.snapshot(status)

        return {
            "status": snapshot.status,
            "events": snapshot.events,
            "runs": snapshot.runs,
            "completed": snapshot.completed,
            "failed": snapshot.failed,
            "average_duration_seconds": (
                snapshot.average_duration_seconds
            ),
        }
