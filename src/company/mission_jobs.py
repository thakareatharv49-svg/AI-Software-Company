from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from src.company.mission_controller.models import MissionPlan
from src.company.models.contracts import CompanyMission
from src.security.redaction import redact_sensitive_text


class MissionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS: dict[MissionJobStatus, frozenset[MissionJobStatus]] = {
    MissionJobStatus.QUEUED: frozenset({MissionJobStatus.RUNNING, MissionJobStatus.FAILED, MissionJobStatus.CANCELLED}),
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
    workspace_id: str | None = None
    # Old persisted jobs may contain negative counters. Normalize them on load
    # so one malformed legacy record cannot be quarantined or hide other jobs.
    attempts: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("attempts", mode="before")
    @classmethod
    def normalize_attempts(cls, value: object) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError, OverflowError):
            return 0

    @field_validator("message", mode="before")
    @classmethod
    def sanitize_message(cls, value: object) -> str:
        """Redact and bound job diagnostics before they are persisted or exposed."""
        return redact_sensitive_text(str(value))[:4000]


def recover_running_plan(plan: MissionPlan) -> MissionPlan:
    """Make interrupted in-flight stages safe to retry after a process restart."""
    recovered = plan.model_copy(deep=True)
    for step in recovered.steps:
        if str(getattr(step.status, "value", step.status)).strip().casefold() == "running":
            step.status = "planned"
            step.detail = None
    return recovered


def recover_running_job(job: MissionJob) -> MissionJob:
    if job.status != MissionJobStatus.RUNNING:
        return job
    recovered_plan = recover_running_plan(job.plan)
    recovered = job.model_copy(update={"plan": recovered_plan})
    return transition_job(
        recovered,
        MissionJobStatus.QUEUED,
        "Recovered after process restart; interrupted stage will be retried.",
    )


def transition_job(job: MissionJob, target: MissionJobStatus, message: str) -> MissionJob:
    if target == job.status:
        return job.model_copy(update={"message": message, "updated_at": datetime.now(UTC)})
    if target not in _ALLOWED_TRANSITIONS[job.status]:
        raise ValueError(f"Invalid mission transition: {job.status.value} -> {target.value}")
    safe_message = redact_sensitive_text(str(message))[:4000]
    return job.model_copy(
        update={
            "status": target,
            "message": safe_message,
            "updated_at": datetime.now(UTC),
        }
    )
