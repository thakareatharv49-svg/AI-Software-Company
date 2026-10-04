
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class RuntimeObservation:
    timestamp: str
    event: str
    run_id: str | None
    status: str | None
    duration_seconds: float | None
    metadata: dict[str, Any]


class RuntimeObservability:
    def __init__(self, log_path: str | Path | None = None) -> None:
        self.log_path = Path(log_path) if log_path else None
        self._events: list[RuntimeObservation] = []
        self._lock = Lock()

    def record(
        self,
        event: str,
        *,
        run_id: str | None = None,
        status: str | None = None,
        duration_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeObservation:
        observation = RuntimeObservation(
            timestamp=datetime.now(UTC).isoformat(),
            event=event,
            run_id=run_id,
            status=status,
            duration_seconds=duration_seconds,
            metadata=dict(metadata or {}),
        )

        with self._lock:
            self._events.append(observation)

            if self.log_path:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(asdict(observation)) + "\n")

        return observation

    def events(
        self,
        *,
        run_id: str | None = None,
        event: str | None = None,
    ) -> list[RuntimeObservation]:
        with self._lock:
            result = list(self._events)

        if run_id is not None:
            result = [item for item in result if item.run_id == run_id]

        if event is not None:
            result = [item for item in result if item.event == event]

        return result

    def count(self, event: str | None = None) -> int:
        return len(self.events(event=event))

    def summary(self) -> dict[str, Any]:
        events = self.events()

        durations = [
            item.duration_seconds
            for item in events
            if item.duration_seconds is not None
        ]

        statuses: dict[str, int] = {}
        for item in events:
            if item.status:
                statuses[item.status] = statuses.get(item.status, 0) + 1

        return {
            "events": len(events),
            "statuses": statuses,
            "duration_count": len(durations),
            "duration_total_seconds": sum(durations),
            "duration_average_seconds": (
                sum(durations) / len(durations) if durations else 0.0
            ),
        }


class RuntimeOperationTimer:
    def __init__(
        self,
        observability: RuntimeObservability,
        event: str,
        *,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.observability = observability
        self.event = event
        self.run_id = run_id
        self.metadata = metadata or {}
        self.started_at = 0.0

    def __enter__(self) -> RuntimeOperationTimer:
        self.started_at = time.perf_counter()
        self.observability.record(
            f"{self.event}.started",
            run_id=self.run_id,
            metadata=self.metadata,
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        duration = time.perf_counter() - self.started_at
        status = "failed" if exc_type else "completed"

        self.observability.record(
            f"{self.event}.{status}",
            run_id=self.run_id,
            status=status,
            duration_seconds=duration,
            metadata=self.metadata,
        )
