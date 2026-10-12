from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.company import customer_factory_routes
from src.company.mission_jobs import MissionJobStatus


def _job(mission_id: str, workspace_id: str):
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=mission_id,
        workspace_id=workspace_id,
        mission=SimpleNamespace(name=mission_id, objective="Test workspace boundary"),
        status=MissionJobStatus.BLOCKED,
        message="blocked",
        attempts=0,
        plan=SimpleNamespace(steps=[]),
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_customer_mission_list_filters_out_other_workspaces() -> None:
    own = _job("mission-own", "workspace-a")
    foreign = _job("mission-foreign", "workspace-b")
    center = SimpleNamespace(mission_jobs=lambda: [own, foreign])
    context = (SimpleNamespace(id="user-a"), SimpleNamespace(id="workspace-a"))

    response = await customer_factory_routes.list_customer_missions(context, center)

    assert [item["id"] for item in response["items"]] == ["mission-own"]


@pytest.mark.asyncio
async def test_customer_cannot_read_another_workspaces_mission() -> None:
    foreign = _job("mission-foreign", "workspace-b")
    center = SimpleNamespace(mission_job=lambda _mission_id: foreign)
    context = (SimpleNamespace(id="user-a"), SimpleNamespace(id="workspace-a"))

    with pytest.raises(HTTPException) as exc:
        await customer_factory_routes.get_customer_mission(
            "mission-foreign", context, center
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_customer_cannot_read_another_workspaces_outputs() -> None:
    foreign = _job("mission-foreign", "workspace-b")
    output_calls = []
    center = SimpleNamespace(
        mission_job=lambda _mission_id: foreign,
        project_outputs=lambda _mission_id: output_calls.append(_mission_id) or [],
    )
    context = (SimpleNamespace(id="user-a"), SimpleNamespace(id="workspace-a"))

    with pytest.raises(HTTPException) as exc:
        await customer_factory_routes.get_customer_mission_outputs(
            "mission-foreign", context, center
        )

    assert exc.value.status_code == 404
    assert output_calls == []


@pytest.mark.asyncio
async def test_customer_cannot_retry_another_workspaces_mission() -> None:
    foreign = _job("mission-foreign", "workspace-b")
    center = SimpleNamespace(
        factory_running=lambda: False,
        mission_job=lambda _mission_id: foreign,
    )
    context = (SimpleNamespace(id="user-a"), SimpleNamespace(id="workspace-a"))

    with pytest.raises(HTTPException) as exc:
        await customer_factory_routes.retry_customer_mission(
            "mission-foreign", context, object(), center
        )

    assert exc.value.status_code == 404
