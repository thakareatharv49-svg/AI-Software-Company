from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeatureCandidate:
    name: str
    impact: float
    confidence: float
    effort: float


class FeaturePrioritizer:
    """Scores feature candidates using impact, confidence, and effort."""

    def rank(self, candidates: list[FeatureCandidate]) -> tuple[FeatureCandidate, ...]:
        return tuple(
            sorted(
                candidates,
                key=lambda item: (item.impact * item.confidence) / max(item.effort, 0.1),
                reverse=True,
            )
        )
