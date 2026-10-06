from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompetitorProfile:
    name: str
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    pricing: str = ""
    positioning: str = ""


@dataclass(frozen=True, slots=True)
class MarketSignal:
    name: str
    score: float
    evidence_count: int


class CompetitiveIntelligence:
    """Turns competitor profiles into comparable market signals."""

    def analyze(self, competitors: list[CompetitorProfile]) -> list[MarketSignal]:
        signals = [
            MarketSignal(
                name=competitor.name,
                score=max(0.0, len(competitor.strengths) - len(competitor.weaknesses)),
                evidence_count=(
                    len(competitor.strengths) + len(competitor.weaknesses)
                ),
            )
            for competitor in competitors
        ]
        return sorted(signals, key=lambda item: item.score, reverse=True)

    def gaps(self, competitors: list[CompetitorProfile]) -> tuple[str, ...]:
        weaknesses = {
            weakness
            for competitor in competitors
            for weakness in competitor.weaknesses
        }
        strengths = {
            strength
            for competitor in competitors
            for strength in competitor.strengths
        }
        return tuple(sorted(weaknesses - strengths))
