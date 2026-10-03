from pydantic import BaseModel


class DashboardSummary(BaseModel):
    projects: int
    active_projects: int
    completed_projects: int
    agents: int
    available_agents: int
    busy_agents: int
    tasks: int
    completed_tasks: int
    blocked_tasks: int
    memories: int


class DashboardHealth(BaseModel):
    status: str
    services: dict[str, str]
