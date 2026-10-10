from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models.workspace import WorkspaceModel
from src.security.routes.oauth_routes import (
    _COMPANY_WORKSPACE_ID,
    _ensure_company_workspace,
)


@pytest.mark.asyncio
async def test_company_workspace_is_created_before_membership_can_be_added() -> None:
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()

    now = datetime.now(UTC)
    workspace = await _ensure_company_workspace(db, now)

    assert isinstance(workspace, WorkspaceModel)
    assert workspace.id == _COMPANY_WORKSPACE_ID
    assert workspace.kind == "company"
    assert workspace.name == "AI Software Company"
    db.add.assert_called_once_with(workspace)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_company_workspace_is_reused() -> None:
    existing = WorkspaceModel(
        id=_COMPANY_WORKSPACE_ID,
        name="AI Software Company",
        kind="company",
        owner_user_id=None,
        expires_at=None,
        created_at=datetime.now(UTC),
    )
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()

    workspace = await _ensure_company_workspace(db, datetime.now(UTC))

    assert workspace is existing
    db.add.assert_not_called()
    db.flush.assert_not_awaited()
