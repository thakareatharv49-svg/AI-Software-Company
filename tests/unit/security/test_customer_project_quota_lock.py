from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.company.customer_project_routes import ProjectCreate, create_project
from src.db.models.entitlement import WorkspaceEntitlementModel
from src.db.models.project import ProjectModel
from src.db.models.workspace import WorkspaceModel


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class FakeDatabase:
    def __init__(self, workspace):
        self.workspace = workspace
        self.statements = []
        self.added = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement):
        self.statements.append(statement)
        entity = statement.column_descriptions[0].get("entity")
        if entity is WorkspaceModel:
            return FakeResult(self.workspace)
        if entity is WorkspaceEntitlementModel:
            return FakeResult(None)
        return FakeResult(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_project_quota_check_locks_workspace_row() -> None:
    workspace = SimpleNamespace(id="workspace-a")
    db = FakeDatabase(workspace)
    result = await create_project(
        ProjectCreate(name="New project"),
        (SimpleNamespace(id="user-a"), workspace),
        db,
    )

    workspace_queries = [
        statement for statement in db.statements
        if statement.column_descriptions[0].get("entity") is WorkspaceModel
    ]
    assert len(workspace_queries) == 1
    assert workspace_queries[0]._for_update_arg is not None
    assert result["workspace_id"] == "workspace-a"
    assert db.committed is True


@pytest.mark.asyncio
async def test_project_creation_fails_closed_if_workspace_disappears() -> None:
    workspace = SimpleNamespace(id="workspace-missing")
    db = FakeDatabase(None)

    with pytest.raises(HTTPException) as exc:
        await create_project(
            ProjectCreate(name="Should not exist"),
            (SimpleNamespace(id="user-a"), workspace),
            db,
        )

    assert exc.value.status_code == 404
    assert db.added == []
    assert db.rolled_back is True
    assert db.committed is False
