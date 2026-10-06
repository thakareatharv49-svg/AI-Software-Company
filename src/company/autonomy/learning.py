from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompanyLearning:
    observations: tuple[str, ...]
    lessons: tuple[str, ...]
    confidence: float


class LearningService:
    def learn(
        self, observations: list[str], lessons: list[str], confidence: float = 0.0
    ) -> CompanyLearning:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return CompanyLearning(tuple(observations), tuple(lessons), confidence)
