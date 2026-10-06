from __future__ import annotations

from dataclasses import dataclass

from company.autonomy.learning import CompanyLearning
from company.autonomy.portfolio import ProductPortfolio
from company.autonomy.resources import ResourceAllocation
from company.autonomy.selection import ProjectCandidate, ProjectSelector


@dataclass(frozen=True, slots=True)
class AutonomyCycle:
    selected_project: str | None
    allocation: ResourceAllocation | None
    learning: CompanyLearning
    status: str


class CompanyAutonomy:
    """Coordinates the final company decision loop without bypassing safety gates."""

    def run_cycle(
        self,
        portfolio: ProductPortfolio,
        candidates: list[ProjectCandidate],
        allocation: ResourceAllocation | None,
        learning: CompanyLearning,
    ) -> AutonomyCycle:
        candidate = ProjectSelector().select(candidates)
        if candidate is None:
            return AutonomyCycle(None, None, learning, "idle")
        return AutonomyCycle(candidate.name, allocation, learning, "planned")
