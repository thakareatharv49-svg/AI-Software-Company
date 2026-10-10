"""Customer-facing workspace and quota endpoints."""
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.company.customer_entitlements import DEFAULT_CUSTOMER_PLAN, PLAN_LIMITS, can_consume_run, resolve_limits
from src.company.customer_project_routes import router as customer_project_router
from src.company.customer_factory_routes import router as customer_factory_router
from src.db.models.entitlement import WorkspaceEntitlementModel, WorkspaceUsageModel
from src.db.session import get_db
from src.security.customer_authorization import require_customer_workspace

router = APIRouter(prefix="/api/customer", tags=["customer-workspace"])

async def _entitlement(db: AsyncSession, workspace_id: str) -> WorkspaceEntitlementModel:
    result = await db.execute(select(WorkspaceEntitlementModel).where(WorkspaceEntitlementModel.workspace_id == workspace_id))
    entitlement = result.scalar_one_or_none()
    if entitlement is None:
        entitlement = WorkspaceEntitlementModel(workspace_id=workspace_id, plan=DEFAULT_CUSTOMER_PLAN, status="active", monthly_run_limit=PLAN_LIMITS[DEFAULT_CUSTOMER_PLAN].monthly_runs, project_limit=PLAN_LIMITS[DEFAULT_CUSTOMER_PLAN].projects, updated_at=datetime.now(UTC))
        db.add(entitlement)
        await db.flush()
    return entitlement

def _period_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

@router.get("/workspace")
async def get_customer_workspace(context: Annotated[tuple, Depends(require_customer_workspace)], db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, object]:
    user, workspace = context
    entitlement = await _entitlement(db, workspace.id)
    period = _period_start(datetime.now(UTC))
    result = await db.execute(select(WorkspaceUsageModel).where(WorkspaceUsageModel.workspace_id == workspace.id, WorkspaceUsageModel.period_start == period))
    usage = result.scalar_one_or_none()
    limits = resolve_limits(entitlement.plan, status=entitlement.status)
    await db.commit()
    return {"user": {"id": user.id, "email": user.email, "display_name": user.display_name}, "workspace": {"id": workspace.id, "name": workspace.name, "kind": workspace.kind}, "plan": entitlement.plan, "subscription_status": entitlement.status, "usage": {"period_start": period.isoformat(), "runs_used": usage.runs_used if usage else 0, "monthly_run_limit": min(entitlement.monthly_run_limit, limits.monthly_runs), "project_limit": min(entitlement.project_limit, limits.projects)}}

@router.post("/usage/consume-run")
async def consume_customer_run(context: Annotated[tuple, Depends(require_customer_workspace)], db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, object]:
    """Charge one run to this authenticated workspace; clients cannot choose workspace IDs."""
    _, workspace = context
    now = datetime.now(UTC)
    period = _period_start(now)
    entitlement = await _entitlement(db, workspace.id)
    limits = resolve_limits(entitlement.plan, status=entitlement.status)
    limit = min(entitlement.monthly_run_limit, limits.monthly_runs)
    result = await db.execute(select(WorkspaceUsageModel).where(WorkspaceUsageModel.workspace_id == workspace.id, WorkspaceUsageModel.period_start == period).with_for_update())
    usage = result.scalar_one_or_none()
    if usage is None:
        usage = WorkspaceUsageModel(id=str(uuid4()), workspace_id=workspace.id, period_start=period, runs_used=0, updated_at=now)
        db.add(usage)
        await db.flush()
    if not can_consume_run(runs_used=usage.runs_used, limit=limit, status=entitlement.status):
        await db.rollback()
        raise HTTPException(status_code=429, detail="Monthly run quota exhausted or subscription inactive")
    usage.runs_used += 1
    usage.updated_at = now
    await db.commit()
    return {"accepted": True, "runs_used": usage.runs_used, "monthly_run_limit": limit, "remaining": max(0, limit - usage.runs_used)}


router.include_router(customer_project_router)
router.include_router(customer_factory_router)
