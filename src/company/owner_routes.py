"""Private owner administration endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import UserModel
from src.db.models.workspace import WorkspaceModel
from src.db.session import get_db

router = APIRouter(prefix="/api/owner", tags=["owner-admin"])


@router.get("/customers")
async def list_customer_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    """List registered accounts and personal workspace metadata for owner operations.

    This endpoint is mounted behind require_company_owner in src.main. It returns
    account/workspace metadata only; it never returns OAuth tokens or sessions.
    """
    total_result = await db.execute(
        select(func.count()).select_from(UserModel)
    )
    total = int(total_result.scalar_one())

    result = await db.execute(
        select(UserModel, WorkspaceModel)
        .outerjoin(
            WorkspaceModel,
            (WorkspaceModel.owner_user_id == UserModel.id)
            & (WorkspaceModel.kind == "personal"),
        )
        .order_by(UserModel.created_at.desc())
        .limit(100)
    )
    customers = []
    for user, workspace in result.all():
        customers.append(
            {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "workspace": (
                    {
                        "id": workspace.id,
                        "name": workspace.name,
                        "kind": workspace.kind,
                    }
                    if workspace is not None
                    else None
                ),
            }
        )
    return {"total_accounts": total, "returned": len(customers), "customers": customers}
