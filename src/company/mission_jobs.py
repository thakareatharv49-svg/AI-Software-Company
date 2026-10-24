from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from src.company.mission_controller.models import MissionPlan
from src.company.models.contracts import CompanyMission
from src.security.redaction import redact_sensitive_text


MAX_MISSION_ATTEMPTS = 1_000_000


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
            return min(MAX_MISSION_ATTEMPTS, max(0, int(value)))
        except (TypeError, ValueError, OverflowError):
            return 0

    @field_validator("message", mode="before")
    @classmethod
    def sanitize_message(cls, value: object) -> str:
        """Redact and bound job diagnostics before they are persisted or exposed."""
        return redact_sensitive_text(str(value))[:4000]


def _recover_engineering_tasks(plan: MissionPlan, *, retry_failed: bool) -> None:
    """Reset interrupted task leases and invalidate stale completed descendants."""
    for task in plan.engineering_tasks:
        status = str(getattr(task.status, "value", task.status)).strip().casefold()
        if status == "running" or (retry_failed and status == "failed"):
            task.status = "planned"
            task.detail = None

    # Dependency-first order makes invalidation deterministic and propagates
    # from reset prerequisites to any descendants that had stale completion.
    try:
        ordered = plan.engineering_task_order()
    except ValueError:
        # Leave malformed graph details intact for the execution preflight to
        # reject explicitly; recovery must not guess at an invalid dependency DAG.
        return
    completed: set[str] = set()
    for task in ordered:
        status = str(getattr(task.status, "value", task.status)).strip().casefold()
        if status == "completed" and not set(task.depends_on).issubset(completed):
            task.status = "planned"
            task.detail = None
            status = "planned"
        if status == "completed":
            completed.add(task.id)


def recover_running_plan(plan: MissionPlan) -> MissionPlan:
    """Make interrupted in-flight stages and engineering tasks safe to resume."""
    recovered = plan.model_copy(deep=True)
    for step in recovered.steps:
        if str(getattr(step.status, "value", step.status)).strip().casefold() == "running":
            step.status = "planned"
            step.detail = None
    _recover_engineering_tasks(recovered, retry_failed=True)
    return recovered


def resume_failed_plan(plan: MissionPlan) -> MissionPlan:
    """Resume from the earliest failed/in-flight checkpoint without replaying valid work.

    Failed and interrupted stages are retried. A completed stage is retained only
    when all of its declared prerequisites are still completed; invalidation then
    propagates through completed dependents. Attempt counters remain intact.
    """
    recovered = plan.model_copy(deep=True)
    completed_status = "completed"
    retryable_statuses = {"failed", "running"}
    for step in recovered.steps:
        status = str(getattr(step.status, "value", step.status)).strip().casefold()
        if status in retryable_statuses:
            step.status = "planned"
            step.detail = None
    _recover_engineering_tasks(recovered, retry_failed=True)

    changed = True
    while changed:
        changed = False
        completed = {
            step.stage.value
            for step in recovered.steps
            if str(getattr(step.status, "value", step.status)).strip().casefold()
            == completed_status
        }
        for step in recovered.steps:
            status = str(getattr(step.status, "value", step.status)).strip().casefold()
            if status != completed_status:
                continue
            if not set(step.depends_on).issubset(completed):
                step.status = "planned"
                step.detail = None
                changed = True

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
