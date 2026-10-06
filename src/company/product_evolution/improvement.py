from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImprovementPlan:
    product: str
    actions: tuple[str, ...]
    rationale: str


class ContinuousImprovement:
    """Turns measured product signals into reviewable improvement plans."""

    def plan(
        self, product: str, actions: list[str], rationale: str
    ) -> ImprovementPlan:
        if not product.strip() or not rationale.strip():
            raise ValueError("product and rationale must not be empty")
        return ImprovementPlan(product, tuple(actions), rationale)
