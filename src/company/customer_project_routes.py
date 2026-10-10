"""Workspace-scoped customer project API."""
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.company.customer_entitlements import PLAN_LIMITS, resolve_limits
from src.db.models.entitlement import WorkspaceEntitlementModel
from src.db.models.project import ProjectModel
from src.db.session import get_db
from src.security.customer_authorization import require_customer_workspace

router = APIRouter(prefix="/projects", tags=["customer-projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)
    objective: str = Field(default="", max_length=20000)


@router.get("")
async def list_projects(
    context: Annotated[tuple, Depends(require_customer_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    _, workspace = context
    result = await db.execute(select(ProjectModel).where(
        ProjectModel.workspace_id == workspace.id
    ).order_by(ProjectModel.created_at.desc()))
    projects = result.scalars().all()
    return {"items": [{"id": p.id, "name": p.name, "description": p.description,
                       "objective": p.objective, "status": p.status,
                       "repository": p.repository, "created_at": p.created_at.isoformat()}
                      for p in projects]}


@router.post("", status_code=201)
async def create_project(
    payload: ProjectCreate,
    context: Annotated[tuple, Depends(require_customer_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    _, workspace = context
    result = await db.execute(select(WorkspaceEntitlementModel).where(
        WorkspaceEntitlementModel.workspace_id == workspace.id
    ))
    entitlement = result.scalar_one_or_none()
    if entitlement is None:
        entitlement = WorkspaceEntitlementModel(
            workspace_id=workspace.id, plan="demo", status="active",
            monthly_run_limit=PLAN_LIMITS["demo"].monthly_runs,
            project_limit=PLAN_LIMITS["demo"].projects, updated_at=datetime.now(UTC),
        )
        db.add(entitlement)
        await db.flush()
    limits = resolve_limits(entitlement.plan, status=entitlement.status)
    limit = min(entitlement.project_limit, limits.projects)
    result = await db.execute(select(func.count()).select_from(ProjectModel).where(
        ProjectModel.workspace_id == workspace.id
    ))
    count = int(result.scalar_one())
    if count >= limit:
        await db.rollback()
        raise HTTPException(status_code=429, detail="Workspace project limit reached or subscription inactive")
    now = datetime.now(UTC)
    project = ProjectModel(
        id=str(uuid4()), workspace_id=workspace.id, name=payload.name.strip(),
        description=payload.description, objective=payload.objective,
        repository=None, status="planned", created_at=now, updated_at=now,
    )
    if not project.name:
        raise HTTPException(status_code=422, detail="Project name cannot be blank")
    db.add(project)
    await db.commit()
    return {"id": project.id, "name": project.name, "description": project.description,
            "objective": project.objective, "status": project.status,
            "workspace_id": workspace.id}
