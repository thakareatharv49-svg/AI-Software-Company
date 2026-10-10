"""Customer-safe factory launch and mission result APIs.

Every lookup is scoped to the authenticated personal workspace. Customer clients
never supply a workspace ID or gain access to company-owner control endpoints.
"""
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.company.control_center.routes import get_control_center
from src.company.control_center.service import CompanyControlCenter, MissionSubmission
from src.company.customer_entitlements import (
    DEFAULT_CUSTOMER_PLAN,
    PLAN_LIMITS,
    can_consume_run,
    resolve_limits,
)
from src.company.mission_jobs import MissionJobStatus
from src.db.models.entitlement import WorkspaceEntitlementModel, WorkspaceUsageModel
from src.db.models.project import ProjectModel
from src.db.session import get_db
from src.security.customer_authorization import require_customer_workspace

router = APIRouter(tags=["customer-factory"])


def _period_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _ensure_entitlement(
    db: AsyncSession, workspace_id: str
) -> WorkspaceEntitlementModel:
    result = await db.execute(
        select(WorkspaceEntitlementModel)
        .where(WorkspaceEntitlementModel.workspace_id == workspace_id)
        .with_for_update()
    )
    entitlement = result.scalar_one_or_none()
    if entitlement is None:
        entitlement = WorkspaceEntitlementModel(
            workspace_id=workspace_id,
            plan=DEFAULT_CUSTOMER_PLAN,
            status="active",
            monthly_run_limit=PLAN_LIMITS[DEFAULT_CUSTOMER_PLAN].monthly_runs,
            project_limit=PLAN_LIMITS[DEFAULT_CUSTOMER_PLAN].projects,
            updated_at=datetime.now(UTC),
        )
        db.add(entitlement)
        await db.flush()
        # Serialize subsequent launches against the row we just provisioned.
        result = await db.execute(
            select(WorkspaceEntitlementModel)
            .where(WorkspaceEntitlementModel.workspace_id == workspace_id)
            .with_for_update()
        )
        entitlement = result.scalar_one()
    return entitlement


@router.post("/projects/{project_id}/launch", status_code=202)
async def launch_customer_project(
    project_id: str,
    context: Annotated[tuple, Depends(require_customer_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> dict[str, object]:
    """Launch one workspace-owned project and charge quota exactly once."""
    _, workspace = context
    if center.factory_running():
        raise HTTPException(
            status_code=409,
            detail="The factory is busy; retry this launch when it is idle",
        )

    project_result = await db.execute(
        select(ProjectModel)
        .where(
            ProjectModel.id == project_id,
            ProjectModel.workspace_id == workspace.id,
        )
        .with_for_update()
    )
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.mission_id:
        job = center.mission_job(project.mission_id)
        if job is None or job.workspace_id != workspace.id:
            raise HTTPException(status_code=409, detail="Linked mission is unavailable")
        if job.status == MissionJobStatus.QUEUED and not center.factory_running():
            try:
                center.enqueue_factory_mission(job.id)
                await center.run_factory(max_projects=1, max_retries=2, mission_id=job.id)
            except (RuntimeError, ValueError, KeyError) as exc:
                raise HTTPException(status_code=409, detail=f"Mission remains queued: {exc}") from exc
        return {
            "accepted": True,
            "already_launched": True,
            "project_id": project.id,
            "mission_id": project.mission_id,
            "status": job.status.value,
        }
    if project.status != "planned":
        raise HTTPException(
            status_code=409,
            detail=f"Project cannot be launched from status '{project.status}'",
        )

    now = datetime.now(UTC)
    period = _period_start(now)
    entitlement = await _ensure_entitlement(db, workspace.id)
    limits = resolve_limits(entitlement.plan, status=entitlement.status)
    limit = min(entitlement.monthly_run_limit, limits.monthly_runs)
    if not can_consume_run(runs_used=0, limit=limit, status=entitlement.status):
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="Monthly run quota exhausted or subscription inactive",
        )

    usage_result = await db.execute(
        select(WorkspaceUsageModel).where(
            WorkspaceUsageModel.workspace_id == workspace.id,
            WorkspaceUsageModel.period_start == period,
        ).with_for_update()
    )
    usage = usage_result.scalar_one_or_none()
    if usage is None:
        usage = WorkspaceUsageModel(
            id=str(uuid4()),
            workspace_id=workspace.id,
            period_start=period,
            runs_used=0,
            updated_at=now,
        )
        db.add(usage)
        await db.flush()
    if not can_consume_run(
        runs_used=usage.runs_used, limit=limit, status=entitlement.status
    ):
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="Monthly run quota exhausted or subscription inactive",
        )

    objective_parts = [project.objective.strip(), project.description.strip()]
    objective = "\n\n".join(part for part in objective_parts if part)
    if not objective:
        objective = f"Build a working software product named {project.name}."
    submission = MissionSubmission(name=project.name, objective=objective)

    try:
        record = center.submit_mission(submission, workspace_id=workspace.id)
        center.enqueue_factory_mission(record.mission.id)
    except (RuntimeError, ValueError, KeyError) as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    usage.runs_used += 1
    usage.updated_at = now
    project.mission_id = record.mission.id
    project.status = "queued"
    project.updated_at = now
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    try:
        await center.run_factory(
            max_projects=1,
            max_retries=2,
            mission_id=record.mission.id,
        )
    except (RuntimeError, ValueError, KeyError) as exc:
        # The job remains durable and visible, but launch did not start. Avoid
        # silently refunding a quota for a mission that was successfully queued.
        raise HTTPException(
            status_code=409,
            detail=f"Mission queued but factory could not start: {exc}",
        ) from exc

    return {
        "accepted": True,
        "already_launched": False,
        "project_id": project.id,
        "mission_id": record.mission.id,
        "status": MissionJobStatus.QUEUED.value,
        "runs_used": usage.runs_used,
        "monthly_run_limit": limit,
        "remaining": max(0, limit - usage.runs_used),
    }


@router.get("/missions")
async def list_customer_missions(
    context: Annotated[tuple, Depends(require_customer_workspace)],
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> dict[str, object]:
    _, workspace = context
    jobs = [
        job for job in center.mission_jobs()
        if job.workspace_id == workspace.id
    ]
    return {
        "items": [
            {
                "id": job.id,
                "name": job.mission.name,
                "objective": job.mission.objective,
                "status": job.status.value,
                "message": job.message,
                "attempts": job.attempts,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
            }
            for job in jobs
        ]
    }


@router.get("/missions/{mission_id}")
async def get_customer_mission(
    mission_id: str,
    context: Annotated[tuple, Depends(require_customer_workspace)],
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> dict[str, object]:
    _, workspace = context
    job = center.mission_job(mission_id)
    if job is None or job.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {
        "id": job.id,
        "name": job.mission.name,
        "objective": job.mission.objective,
        "status": job.status.value,
        "message": job.message,
        "attempts": job.attempts,
        "plan": job.plan.model_dump(mode="json"),
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@router.get("/missions/{mission_id}/outputs")
async def get_customer_mission_outputs(
    mission_id: str,
    context: Annotated[tuple, Depends(require_customer_workspace)],
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> dict[str, object]:
    _, workspace = context
    job = center.mission_job(mission_id)
    if job is None or job.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {
        "mission_id": mission_id,
        "items": [
            item.model_dump(mode="json")
            for item in center.project_outputs(mission_id)
        ],
    }
