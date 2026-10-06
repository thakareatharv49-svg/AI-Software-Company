from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean


@dataclass(frozen=True, slots=True)
class LearningSignal:
    category: str
    outcome: str
    value: float
    project_id: str | None = None
    timestamp: datetime = datetime.now(UTC)


class LearningEngine:
    """Turns execution outcomes into measurable reusable lessons."""

    def __init__(self) -> None:
        self._signals: list[LearningSignal] = []

    def record(self, signal: LearningSignal) -> LearningSignal:
        self._signals.append(signal)
        return signal

    def signals(self, category: str | None = None) -> list[LearningSignal]:
        if category is None:
            return list(self._signals)
        return [s for s in self._signals if s.category == category]

    def success_rate(self, category: str | None = None) -> float:
        signals = self.signals(category)
        if not signals:
            return 0.0
        return sum(s.value > 0 for s in signals) / len(signals)

    def average(self, category: str) -> float:
        values = [s.value for s in self.signals(category)]
        return mean(values) if values else 0.0

    def lessons(self, category: str | None = None) -> list[str]:
        signals = self.signals(category)
        if not signals:
            lessons = [(outcome, mean(values), f"{outcome}: average={mean(values):.3f}, samples={len(values)}") for outcome, values in grouped.items()]
        lessons.sort(key=lambda item: item[1], reverse=True)
        return [lesson[2] for lesson in lessons]
