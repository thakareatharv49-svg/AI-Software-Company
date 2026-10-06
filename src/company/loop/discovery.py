from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Opportunity:
    opportunity_id: str
    title: str
    description: str
    expected_value: float
    confidence: float = 1.0
    risk: float = 0.0
    estimated_cost: float = 0.0


class OpportunityDiscovery:
    """Normalizes externally discovered opportunities for autonomous selection."""

    def discover(self, candidates: list[Opportunity]) -> list[Opportunity]:
        return sorted(
            candidates,
            key=lambda item: (
                item.expected_value * item.confidence
                - item.risk
                - item.estimated_cost
            ),
            reverse=True,
        )

    def top(self, candidates: list[Opportunity], limit: int = 1) -> list[Opportunity]:
        if limit < 1:
            return []
        return self.discover(candidates)[:limit]
