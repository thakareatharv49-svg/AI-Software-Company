from fastapi import APIRouter

from src.dashboard.models.contracts import DashboardHealth, DashboardSummary
from src.memory.service.service import MemoryService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_memory_service = MemoryService()


@router.get("/health", response_model=DashboardHealth)
def dashboard_health() -> DashboardHealth:
    return DashboardHealth(
        status="healthy",
        services={
            "api": "healthy",
            "memory": "healthy",
        },
    )


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary() -> DashboardSummary:
    return DashboardSummary(
        projects=0,
        active_projects=0,
        completed_projects=0,
        agents=0,
        available_agents=0,
        busy_agents=0,
        tasks=0,
        completed_tasks=0,
        blocked_tasks=0,
        memories=len(_memory_service.store.list_all()),
    )
