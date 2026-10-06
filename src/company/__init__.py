from src.company.models.contracts import (
    CompanyCycleResult,
    CompanyMission,
    CompanyState,
)
from src.company.models.enums import (
    CompanyDecision,
    CompanyStatus,
)
from src.company.orchestration.orchestrator import CompanyOrchestrator

__all__ = [
    "CompanyCycleResult",
    "CompanyDecision",
    "CompanyMission",
    "CompanyOrchestrator",
    "CompanyState",
    "CompanyStatus",
    "FactoryProject",
    "ProjectFactory",
]


def __getattr__(name: str):
    """Lazily expose factory classes to avoid the package import cycle."""
    if name in {"FactoryProject", "ProjectFactory"}:
        from src.company.project_factory import FactoryProject, ProjectFactory

        return {"FactoryProject": FactoryProject, "ProjectFactory": ProjectFactory}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
