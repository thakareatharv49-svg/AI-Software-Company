from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectScore:
    project_id: str
    name: str
    score: float
    expected_value: float
    risk: float
    cost: float
    confidence: float


class PortfolioManager:
    """Ranks projects so company capacity can be allocated to the best opportunities."""

    def rank(self, projects: list[ProjectScore]) -> list[ProjectScore]:
        return sorted(projects, key=lambda project: project.score, reverse=True)

    def select(
        self,
        projects: list[ProjectScore],
        capacity: int,
    ) -> list[ProjectScore]:
        if capacity < 1:
            return []
        return self.rank(projects)[:capacity]

    def score(
        self,
        *,
        project_id: str,
        name: str,
        expected_value: float,
        risk: float,
        cost: float,
        confidence: float,
    ) -> ProjectScore:
        value = expected_value * confidence - risk - cost
        return ProjectScore(
            project_id=project_id,
            name=name,
            score=value,
            expected_value=expected_value,
            risk=risk,
            cost=cost,
            confidence=confidence,
        )
