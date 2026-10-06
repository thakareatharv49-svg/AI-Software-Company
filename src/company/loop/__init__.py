from src.company.loop.lifecycle import LifecycleState, ProjectLifecycle
from src.company.loop.concurrency import ConcurrentProjectRunner, ProjectRunResult
from src.company.loop.self_repair import HealingAction, SelfHealingService
from src.company.loop.discovery import Opportunity, OpportunityDiscovery
from src.company.loop.operating import CompanyOperatingLoop, CompanyCycleResult

__all__ = [
    "LifecycleState",
    "ProjectLifecycle",
    "ConcurrentProjectRunner",
    "ProjectRunResult",
    "HealingAction",
    "SelfHealingService",
    "Opportunity",
    "OpportunityDiscovery",
    "CompanyOperatingLoop",
    "CompanyCycleResult",
]


class CompanyOperatingLoop:
    """Coordinates a bounded company operating cycle."""

    def select(self, project_ids: list[str], capacity: int = 1) -> tuple[str, ...]:
        if capacity < 1:
            return ()
        return tuple(project_ids[:capacity])

    def report(self, selected: list[str], completed: list[str]) -> dict[str, tuple[str, ...]]:
        return {"selected": tuple(selected), "completed": tuple(completed)}
