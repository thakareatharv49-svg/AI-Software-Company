from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.agents.models.contracts import AgentResult
from src.company.audit import MissionAuditEntry
from src.company.control_center.service import (
    CompanyControlCenter,
    MissionRecord,
    MissionSubmission,
    control_center,
)
from src.company.mission_controller.models import MissionPlan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.project_outputs import ProjectOutputManifest
from src.company.readiness import ProductionReadinessReport, build_readiness_report

router = APIRouter(prefix="/api")


def get_control_center() -> CompanyControlCenter:
    return control_center


ControlCenter = Depends(get_control_center)


@router.get("/company/readiness", response_model=ProductionReadinessReport)
def company_readiness() -> ProductionReadinessReport:
    return build_readiness_report()


@router.get("/company/state")
def company_state(center: CompanyControlCenter = ControlCenter):
    return center.state


@router.get("/missions")
def missions(center: CompanyControlCenter = ControlCenter) -> list[MissionRecord]:
    return center.missions()


@router.get("/company/events")
def company_events(center: CompanyControlCenter = ControlCenter):
    return center.events()


@router.post("/missions", status_code=status.HTTP_201_CREATED)
def submit_mission(
    submission: MissionSubmission,
    center: CompanyControlCenter = ControlCenter,
) -> MissionRecord:
    try:
        record = center.submit_mission(submission)
        return record
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/cancel", response_model=MissionJob)
def cancel_mission(
    mission_id: str,
    center: CompanyControlCenter = ControlCenter,
) -> MissionJob:
    try:
        return center.cancel_mission(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Mission job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/retry", response_model=MissionJob)
def retry_mission(
    mission_id: str,
    center: CompanyControlCenter = ControlCenter,
) -> MissionJob:
    try:
        return center.retry_mission(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Mission job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/missions/{mission_id}/outputs", response_model=list[ProjectOutputManifest])
def mission_outputs(
    mission_id: str,
    center: CompanyControlCenter = ControlCenter,
) -> list[ProjectOutputManifest]:
    if center.mission_job(mission_id) is None:
        raise HTTPException(status_code=404, detail="Mission job not found")
    return center.project_outputs(mission_id)


@router.get("/missions/{mission_id}/audit", response_model=list[MissionAuditEntry])
def mission_audit(
    mission_id: str,
    event_type: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, max_length=32),
    center: CompanyControlCenter = ControlCenter,
) -> list[MissionAuditEntry]:
    if center.mission_job(mission_id) is None:
        raise HTTPException(status_code=404, detail="Mission job not found")
    return center.audit(mission_id, event_type=event_type, status=status)


@router.get("/missions/{mission_id}/diagnostics")
def mission_diagnostics(
    mission_id: str,
    center: CompanyControlCenter = ControlCenter,
) -> dict[str, object]:
    """Explain a mission's persisted progress and flag unusually long inactivity."""
    from datetime import UTC, datetime

    job = center.mission_job(mission_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Mission job not found")

    now = datetime.now(UTC)
    updated_at = job.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    idle_seconds = max(0, int((now - updated_at).total_seconds()))
    status_value = job.status.value
    running_steps = [
        step for step in job.plan.steps
        if str(getattr(step.status, "value", step.status)).casefold() == "running"
    ]
    failed_steps = [
        step for step in job.plan.steps
        if str(getattr(step.status, "value", step.status)).casefold() == "failed"
    ]

    diagnosis = "healthy"
    message = "Mission has recent persisted activity."
    recommended_action = "continue_monitoring"
    if status_value == MissionJobStatus.QUEUED.value:
        if idle_seconds >= 300:
            diagnosis = "waiting_for_worker"
            message = "Mission has been queued for at least five minutes without a status update."
            recommended_action = "start_or_check_factory_worker"
        else:
            diagnosis = "queued"
            message = "Mission is waiting in the factory queue."
            recommended_action = "wait_or_start_factory"
    elif status_value == MissionJobStatus.RUNNING.value and idle_seconds >= 2100:
        diagnosis = "possibly_stalled"
        message = (
            "No persisted mission update for over 35 minutes. This may be a stalled "
            "worker; a long model call or external process can also delay updates."
        )
        recommended_action = "inspect_audit_and_worker_before_retrying"
    elif status_value == MissionJobStatus.RUNNING.value:
        diagnosis = "active"
        message = "Mission is running within the expected progress window."
        recommended_action = "continue_monitoring"
    elif status_value == MissionJobStatus.BLOCKED.value:
        diagnosis = "blocked"
        message = job.message
        recommended_action = "review_failure_details_then_retry"
    elif status_value == MissionJobStatus.FAILED.value:
        diagnosis = "failed"
        message = job.message
        recommended_action = "review_failure_details_then_retry"
    elif status_value == MissionJobStatus.CANCELLED.value:
        diagnosis = "cancelled"
        message = job.message
        recommended_action = "submit_or_queue_a_new_mission"
    elif status_value == MissionJobStatus.COMPLETED.value:
        diagnosis = "completed"
        message = "Mission completed."
        recommended_action = "review_product"

    current_step = running_steps[0] if running_steps else None
    failed_step = failed_steps[-1] if failed_steps else None
    return {
        "mission_id": job.id,
        "status": status_value,
        "diagnosis": diagnosis,
        "message": message,
        "recommended_action": recommended_action,
        "idle_seconds": idle_seconds,
        "last_updated_at": job.updated_at.isoformat(),
        "current_stage": current_step.stage.value if current_step else None,
        "current_stage_detail": current_step.detail if current_step else None,
        "failed_stage": failed_step.stage.value if failed_step else None,
        "failure_detail": failed_step.detail if failed_step else (
            job.message if status_value in {
                MissionJobStatus.FAILED.value, MissionJobStatus.BLOCKED.value
            } else None
        ),
        "attempts": job.attempts,
    }


@router.get("/missions/{mission_id}/job", response_model=MissionJob)
def mission_job(
    mission_id: str,
    center: CompanyControlCenter = ControlCenter,
) -> MissionJob:
    job = center.mission_job(mission_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Mission job not found")
    return job


@router.get("/mission-jobs", response_model=list[MissionJob])
def mission_jobs(center: CompanyControlCenter = ControlCenter) -> list[MissionJob]:
    return center.mission_jobs()


@router.post("/missions/cleanup")
def cleanup_missions(center: CompanyControlCenter = ControlCenter) -> dict[str, object]:
    try:
        return center.delete_queued_and_blocked_missions()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/missions/{mission_id}/plan")
def mission_plan(
    mission_id: str,
    center: CompanyControlCenter = ControlCenter,
) -> MissionPlan:
    plan = center.mission_plan(mission_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Mission plan not found")
    return plan


@router.post("/missions/{mission_id}/execute", response_model=AgentResult)
async def execute_mission_stage(
    mission_id: str,
    center: CompanyControlCenter = ControlCenter,
) -> AgentResult:
    try:
        return await center.execute_next_stage(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/execute-all", response_model=list[AgentResult])
async def execute_mission(
    mission_id: str,
    max_stages: int | None = Query(default=None, ge=1, le=12),
    center: CompanyControlCenter = ControlCenter,
) -> list[AgentResult]:
    try:
        return await center.execute_mission(mission_id, max_stages=max_stages)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/company/stop")
def stop_company(center: CompanyControlCenter = ControlCenter):
    return center.stop()


@router.post("/company/block")
def block_company(
    reason: str,
    center: CompanyControlCenter = ControlCenter,
):
    return center.block(reason)


@router.post("/missions/{mission_id}/factory-run")
async def run_factory(
    mission_id: str,
    max_stages: int | None = Query(default=None, ge=1, le=12),
    max_retries: int = Query(default=2, ge=0, le=5),
    center: CompanyControlCenter = ControlCenter,
) -> dict[str, object]:
    try:
        center.enqueue_factory_mission(mission_id)
        await center.run_factory(
            max_projects=1,
            max_stages=max_stages,
            max_retries=max_retries,
            mission_id=mission_id,
        )
        return {"status": "started", "mission_id": mission_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/factory/run-queue")
async def run_factory_queue(
    max_retries: int = Query(default=2, ge=0, le=5),
    center: CompanyControlCenter = ControlCenter,
) -> dict[str, object]:
    """Enable continuous FIFO processing, including projects queued in the future."""
    try:
        queued = [
            job for job in center.mission_jobs()
            if job.status == MissionJobStatus.QUEUED
        ]
        await center.start_continuous_factory(max_retries=max_retries)
        return {
            "status": "continuous",
            "continuous": True,
            "queued_projects": len(queued),
        }
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/factory/continuous/stop")
def stop_continuous_factory(
    center: CompanyControlCenter = ControlCenter,
) -> dict[str, object]:
    was_enabled = center.stop_continuous_factory()
    return {
        "status": "stopping" if was_enabled else "stopped",
        "continuous": False,
        "message": (
            "The current project will finish before the factory stops."
            if was_enabled else "Continuous mode is already stopped."
        ),
    }

@router.get("/factory/status")
def factory_status(center: CompanyControlCenter = ControlCenter) -> dict[str, object]:
    """Expose durable queue state, not only the current process's in-memory queue."""
    jobs = center.mission_jobs()
    counts = {item.value: 0 for item in MissionJobStatus}
    for job in jobs:
        counts[job.status.value] += 1

    queued_jobs = sorted(
        (job for job in jobs if job.status == MissionJobStatus.QUEUED),
        key=lambda item: item.created_at,
    )
    running_jobs = sorted(
        (job for job in jobs if job.status == MissionJobStatus.RUNNING),
        key=lambda item: item.updated_at,
        reverse=True,
    )

    # Prefer the factory's actual order (which may include an explicit priority
    # action), then append durable queued jobs not yet loaded into this process.
    queue_order: list[str] = []
    seen: set[str] = set()
    for project in center._factory.queue:
        mission_id = project.mission.id
        if mission_id not in seen:
            queue_order.append(mission_id)
            seen.add(mission_id)
    for job in queued_jobs:
        if job.id not in seen:
            queue_order.append(job.id)
            seen.add(job.id)

    jobs_by_id = {job.id: job for job in queued_jobs}
    queue_preview = []
    for position, mission_id in enumerate(queue_order[:10], start=1):
        job = jobs_by_id.get(mission_id)
        if job is None:
            project = next(
                (item for item in center._factory.queue if item.mission.id == mission_id),
                None,
            )
            if project is None:
                continue
            queue_preview.append({
                "position": position,
                "mission_id": mission_id,
                "name": project.mission.name,
                "status": project.status,
            })
        else:
            queue_preview.append({
                "position": position,
                "mission_id": job.id,
                "name": job.mission.name,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "attempts": job.attempts,
            })

    active = running_jobs[0] if running_jobs else None
    return {
        "running": center.factory_running(),
        "continuous": center.continuous_factory_enabled(),
        "queued_projects": len(queued_jobs),
        "queue_counts": counts,
        "queue_preview": queue_preview,
        "active_mission": (
            {
                "mission_id": active.id,
                "name": active.mission.name,
                "status": active.status.value,
                "message": active.message,
                "updated_at": active.updated_at.isoformat(),
            }
            if active is not None else None
        ),
    }
