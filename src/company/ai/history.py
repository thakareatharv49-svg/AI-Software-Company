from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from company.ai.observability import AIExecutionObservation


@dataclass(frozen=True)
class AIExecutionHistoryRecord:
    run_id: str
    actor: str
    rounds: int
    tool_calls: int
    stopped_by_limit: bool
    success: bool
    timestamp: str

    @classmethod
    def from_observation(
        cls,
        observation: AIExecutionObservation,
    ) -> AIExecutionHistoryRecord:
        return cls(
            run_id=observation.run_id,
            actor=observation.actor,
            rounds=observation.rounds,
            tool_calls=observation.tool_calls,
            stopped_by_limit=observation.stopped_by_limit,
            success=observation.success,
            timestamp=observation.timestamp,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> AIExecutionHistoryRecord:
        return cls(
            run_id=str(data["run_id"]),
            actor=str(data["actor"]),
            rounds=int(data["rounds"]),
            tool_calls=int(data["tool_calls"]),
            stopped_by_limit=bool(data["stopped_by_limit"]),
            success=bool(data["success"]),
            timestamp=str(data["timestamp"]),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AIExecutionHistoryStore:
    """Append-only JSONL persistence for execution metadata.

    Only execution metadata is persisted. Tool arguments, prompts, outputs,
    and errors are intentionally excluded from history records.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, observation: AIExecutionObservation) -> AIExecutionHistoryRecord:
        record = AIExecutionHistoryRecord.from_observation(observation)

        with self._path.open("a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(record.to_dict(), sort_keys=True))
            file.write("\n")

        return record

    def list(
        self,
        *,
        run_id: str | None = None,
        actor: str | None = None,
    ) -> tuple[AIExecutionHistoryRecord, ...]:
        if not self._path.exists():
            return ()

        records: list[AIExecutionHistoryRecord] = []

        with self._path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                record = AIExecutionHistoryRecord.from_dict(json.loads(line))

                if run_id is not None and record.run_id != run_id:
                    continue

                if actor is not None and record.actor != actor:
                    continue

                records.append(record)

        return tuple(records)

    def get(self, run_id: str) -> AIExecutionHistoryRecord | None:
        for record in self.list(run_id=run_id):
            return record

        return None

    def latest(self) -> AIExecutionHistoryRecord | None:
        records = self.list()

        if not records:
            return None

        return records[-1]
