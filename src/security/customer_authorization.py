"""Customer session and workspace authorization, separate from company-owner access."""
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

async def require_customer_workspace(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> tuple[UserModel, WorkspaceModel]:
    """Resolve only the authenticated user's own personal workspace."""
    token = request.cookies.get("asc_session")
    if not token:
        raise HTTPException(status_code=401, detail="Sign-in required")
    result = await db.execute(select(AuthSessionModel).where(AuthSessionModel.token_hash == hash_session_token(token), AuthSessionModel.revoked.is_(False), AuthSessionModel.expires_at > datetime.now(UTC)))
    session = result.scalar_one_or_none()
    if session is None or not session.user_id:
        raise HTTPException(status_code=401, detail="Session is invalid or expired")
    result = await db.execute(select(UserModel).where(UserModel.id == session.user_id, UserModel.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Account is inactive")
    result = await db.execute(select(WorkspaceModel).join(WorkspaceMembershipModel, WorkspaceMembershipModel.workspace_id == WorkspaceModel.id).where(WorkspaceMembershipModel.user_id == user.id, WorkspaceMembershipModel.role.in_(("owner", "admin", "member")), WorkspaceModel.kind == "personal", WorkspaceModel.owner_user_id == user.id).order_by(WorkspaceModel.created_at.asc()).limit(1))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=403, detail="Personal workspace is not available")
    return user, workspace
