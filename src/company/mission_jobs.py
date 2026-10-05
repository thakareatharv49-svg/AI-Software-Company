from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.company.models.contracts import CompanyMission
from src.company.mission_controller.models import MissionPlan


class MissionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS: dict[MissionJobStatus, frozenset[MissionJobStatus]] = {
    MissionJobStatus.QUEUED: frozenset({MissionJobStatus.RUNNING, MissionJobStatus.CANCELLED}),
    MissionJobStatus.RUNNING: frozenset({
        MissionJobStatus.QUEUED,
        MissionJobStatus.COMPLETED,
        MissionJobStatus.FAILED,
        MissionJobStatus.BLOCKED,
        MissionJobStatus.CANCELLED,
    }),
    MissionJobStatus.COMPLETED: frozenset(),
    MissionJobStatus.FAILED: frozenset({MissionJobStatus.QUEUED}),
    MissionJobStatus.BLOCKED: frozenset({MissionJobStatus.QUEUED}),
    MissionJobStatus.CANCELLED: frozenset(),
}


class MissionJob(BaseModel):
    id: str
    mission: CompanyMission
    plan: MissionPlan
    status: MissionJobStatus
    message: str
    attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def transition_job(job: MissionJob, target: MissionJobStatus, message: str) -> MissionJob:
    if target == job.status:
        return job.model_copy(update={"message": message, "updated_at": datetime.now(UTC)})
    if target not in _ALLOWED_TRANSITIONS[job.status]:
        raise ValueError(f"Invalid mission transition: {job.status.value} -> {target.value}")
    return job.model_copy(
        update={
            "status": target,
            "message": message,
            "updated_at": datetime.now(UTC),
        }
    )
