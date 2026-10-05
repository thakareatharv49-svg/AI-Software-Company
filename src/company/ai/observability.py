from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from company.ai.runtime import AIExecutionResult


@dataclass(frozen=True)
class AIExecutionObservation:
    run_id: str
    actor: str
    rounds: int
    tool_calls: int
    stopped_by_limit: bool
    success: bool
    timestamp: str


class AIExecutionObserver:
    def observe(self, result: AIExecutionResult) -> AIExecutionObservation:
        loop = result.loop
        successful = (
            not loop.stopped_by_limit
            and all(
                getattr(exchange.result.status, "value", exchange.result.status) == "success"
                for exchange in loop.exchanges
            )
        )

        return AIExecutionObservation(
            run_id=result.run_id,
            actor=result.actor,
            rounds=loop.rounds,
            tool_calls=len(loop.exchanges),
            stopped_by_limit=loop.stopped_by_limit,
            success=successful,
            timestamp=datetime.now(UTC).isoformat(),
        )


class AIExecutionObservationStore:
    def __init__(self) -> None:
        self._observations: list[AIExecutionObservation] = []

    def record(self, observation: AIExecutionObservation) -> None:
        self._observations.append(observation)

    def list(self) -> tuple[AIExecutionObservation, ...]:
        return tuple(self._observations)

    def get(self, run_id: str) -> AIExecutionObservation | None:
        for observation in self._observations:
            if observation.run_id == run_id:
                return observation
        return None

    def clear(self) -> None:
        self._observations.clear()
