from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthSignal:
    service: str
    metric: str
    value: float
    threshold: float

    @property
    def unhealthy(self) -> bool:
        return self.value < self.threshold

class ObservabilityService:
    def evaluate(self, signals: list[HealthSignal]) -> dict[str, object]:
        unhealthy = tuple(signal for signal in signals if signal.unhealthy)
        return {"healthy": not unhealthy, "unhealthy": unhealthy, "count": len(signals)}
