from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Feedback:
    source: str
    text: str
    sentiment: float = 0.0


class FeedbackIntelligence:
    """Normalizes feedback into measurable product signals."""

    def summarize(self, feedback: list[Feedback]) -> dict[str, object]:
        if not feedback:
            return {"count": 0, "average_sentiment": 0.0, "themes": ()}
        themes = tuple(sorted({item.source for item in feedback}))
        average = sum(item.sentiment for item in feedback) / len(feedback)
        return {"count": len(feedback), "average_sentiment": average, "themes": themes}
