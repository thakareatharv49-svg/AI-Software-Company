from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectCandidate:
    name: str
    score: float
    risk: float = 0.0


class ProjectSelector:
    def select(self, candidates: list[ProjectCandidate]) -> ProjectCandidate | None:
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.score - item.risk)
