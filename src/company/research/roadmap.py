from __future__ import annotations

from dataclasses import dataclass

from src.company.research.product_discovery import ProductCandidate


@dataclass(frozen=True, slots=True)
class RoadmapItem:
    title: str
    phase: int
    priority: float
    rationale: str


class RoadmapGenerator:
    """Converts product candidates into an execution-ready priority order."""

    def generate(
        self,
        candidates: list[ProductCandidate],
        phases: int = 3,
    ) -> list[RoadmapItem]:
        if phases < 1:
            raise ValueError("phases must be at least 1")
        ranked = sorted(
            candidates,
            key=lambda item: item.score * item.confidence,
            reverse=True,
        )
        return [
            RoadmapItem(
                title=item.name,
                phase=min(index // max(1, len(ranked) // phases or 1) + 1, phases),
                priority=item.score * item.confidence,
                rationale=(
                    f"{item.evidence_count} evidence items; "
                    f"confidence={item.confidence:.2f}."
                ),
            )
            for index, item in enumerate(ranked)
        ]
