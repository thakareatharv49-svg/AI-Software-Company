from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from src.company.models.enums import CompanyDecision, CompanyStatus


class CompanyMission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    objective: str
    constraints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class CompanyState(BaseModel):
    status: CompanyStatus = CompanyStatus.IDLE
    current_project_id: str | None = None
    current_task_id: str | None = None
    completed_projects: int = 0
    completed_tasks: int = 0
    blocked_tasks: int = 0
    last_decision: CompanyDecision | None = None


class CompanyCycleResult(BaseModel):
    decision: CompanyDecision
    message: str
    state: CompanyState
