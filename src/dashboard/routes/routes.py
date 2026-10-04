from fastapi import APIRouter

from src.dashboard.models.contracts import DashboardHealth, DashboardSummary
from src.events.models.contracts import CompanyEvent
from src.events.service.factory import get_event_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_event_service = get_event_service()


@router.get("/health", response_model=DashboardHealth)
def dashboard_health() -> DashboardHealth:
    return DashboardHealth(
        status="healthy",
        services={
            "api": "healthy",
            "events": "healthy",
            "memory": "healthy",
        },
    )


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary() -> DashboardSummary:
    events = _event_service.list_events()

    project_ids = {
        event.project_id
        for event in events
        if event.project_id is not None
    }

    completed_projects = {
        event.project_id
        for event in events
        if event.project_id is not None
        and event.event_type in {
            "project.execution.completed",
            "project.completed",
        }
    }

    failed_projects = {
        event.project_id
        for event in events
        if event.project_id is not None
        and event.event_type in {
            "project.execution.failed",
            "project.failed",
        }
    }

    task_ids = {
        event.task_id
        for event in events
        if event.task_id is not None
    }

    completed_tasks = {
        event.task_id
        for event in events
        if event.task_id is not None
        and event.event_type in {
            "task.completed",
            "task.execution.completed",
        }
    }

    blocked_tasks = {
        event.task_id
        for event in events
        if event.task_id is not None
        and event.event_type in {
            "task.blocked",
            "task.execution.blocked",
        }
    }

    agent_names = {
        event.agent_name
        for event in events
        if event.agent_name
    }

    active_projects = project_ids - completed_projects - failed_projects

    return DashboardSummary(
        projects=len(project_ids),
        active_projects=len(active_projects),
        completed_projects=len(completed_projects),
        agents=len(agent_names),
        available_agents=len(agent_names),
        busy_agents=0,
        tasks=len(task_ids),
        completed_tasks=len(completed_tasks),
        blocked_tasks=len(blocked_tasks),
        memories=len(events),
    )


@router.get("/events", response_model=list[CompanyEvent])
def dashboard_events(
    project_id: str | None = None,
) -> list[CompanyEvent]:
    return _event_service.list_events(project_id=project_id)
