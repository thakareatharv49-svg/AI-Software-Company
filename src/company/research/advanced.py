from __future__ import annotations

from dataclasses import dataclass

from src.company.research.engine import ResearchEngine, ResearchReport


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    query: str
    subqueries: tuple[str, ...]


class AdvancedResearchEngine:
    """Expands a research objective into traceable subqueries."""

    def __init__(self, engine: ResearchEngine) -> None:
        self.engine = engine

    def plan(self, objective: str) -> ResearchPlan:
        normalized = " ".join(objective.split()).strip()
        if not normalized:
            raise ValueError("objective must not be empty")
        return ResearchPlan(
            query=normalized,
            subqueries=(
                normalized,
                f"{normalized} market",
                f"{normalized} alternatives",
                f"{normalized} risks",
            ),
        )

    def research(self, objective: str) -> tuple[ResearchReport, ...]:
        plan = self.plan(objective)
        return tuple(self.engine.research(query) for query in plan.subqueries)
