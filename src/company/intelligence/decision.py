from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecisionOption:
    name: str
    expected_value: float
    risk: float = 0.0
    cost: float = 0.0
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class DecisionResult:
    selected: DecisionOption
    score: float
    rationale: str


class DecisionEngine:
    """Deterministic decision policy using value, confidence, risk and cost."""

    def score(self, option: DecisionOption) -> float:
        return (
            option.expected_value * option.confidence
            - option.risk
            - option.cost
        )

    def choose(self, options: list[DecisionOption]) -> DecisionResult:
        if not options:
            raise ValueError("At least one decision option is required")
        selected = max(options, key=self.score)
        score = self.score(selected)
        return DecisionResult(
            selected=selected,
            score=score,
            rationale=(
                f"Selected {selected.name}: expected value × confidence "
                f"minus risk and cost = {score:.3f}."
            ),
        )
