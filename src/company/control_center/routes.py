import asyncio

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
from src.company.mission_jobs import MissionJob
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
async def submit_mission(
    submission: MissionSubmission,
    center: CompanyControlCenter = ControlCenter,
) -> MissionRecord:
    try:
        record = center.submit_mission(submission)
        center.enqueue_factory_mission(record.mission.id)
        asyncio.create_task(center.run_factory(max_projects=1, max_retries=2))
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
        await center.run_factory(max_projects=1, max_stages=max_stages, max_retries=max_retries)
        return {"status": "started", "mission_id": mission_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/factory/status")
def factory_status(center: CompanyControlCenter = ControlCenter) -> dict[str, object]:
    return {"running": center.factory_running(), "queued_projects": len(center._factory.queue)}
