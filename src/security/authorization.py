"""Authorization dependencies for private company workspace APIs."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.identity import AuthSessionModel
from src.db.models.user import UserModel
from src.db.models.workspace import WorkspaceMembershipModel, WorkspaceModel
from src.db.session import get_db
from src.security.session_tokens import hash_session_token

SESSION_COOKIE = "asc_session"
COMPANY_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"


async def require_company_owner(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserModel:
    """Require a valid server-side session and explicit owner membership.

    Company factory/control-center APIs are private owner operations. Customer
    workspace APIs must use a separate workspace-scoped authorization policy.
    """
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Sign-in required")

    now = datetime.now(UTC)
    session_result = await db.execute(
        select(AuthSessionModel).where(
            AuthSessionModel.token_hash == hash_session_token(raw_token),
            AuthSessionModel.revoked.is_(False),
            AuthSessionModel.expires_at > now,
        )
    )
    session = session_result.scalar_one_or_none()
    if session is None or session.user_id is None:
        raise HTTPException(status_code=401, detail="Session is invalid or expired")

    user_result = await db.execute(select(UserModel).where(UserModel.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")

    workspace_result = await db.execute(
        select(WorkspaceModel).where(
            WorkspaceModel.id == COMPANY_WORKSPACE_ID,
            WorkspaceModel.kind == "company",
        )
    )
    workspace = workspace_result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=503, detail="Company workspace migration is required")

    membership_result = await db.execute(
        select(WorkspaceMembershipModel).where(
            WorkspaceMembershipModel.workspace_id == COMPANY_WORKSPACE_ID,
            WorkspaceMembershipModel.user_id == user.id,
            WorkspaceMembershipModel.role == "owner",
        )
    )
    if membership_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Company owner access required")

    return user
