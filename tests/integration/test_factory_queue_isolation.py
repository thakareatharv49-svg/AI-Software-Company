from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.company.project_factory import ProjectFactory


@pytest.mark.asyncio
async def test_blocked_mission_does_not_stop_later_queued_missions() -> None:
    published_events: list[object] = []
    orchestrator = SimpleNamespace(
        events=SimpleNamespace(publish=published_events.append),
    )
    blocked = SimpleNamespace(
        mission=SimpleNamespace(id="mission-blocked", name="Blocked mission"),
        status="blocked",
    )
    completed = SimpleNamespace(
        mission=SimpleNamespace(id="mission-next", name="Next mission"),
        status="completed",
    )
    factory = ProjectFactory(
        orchestrator=orchestrator,
        controller=None,  # type: ignore[arg-type]
        pipeline=None,  # type: ignore[arg-type]
        queue=[blocked, completed],  # type: ignore[list-item]
    )

    async def fake_run_next(**_kwargs: object) -> object:
        return factory.queue.pop(0)

    factory.run_next = fake_run_next  # type: ignore[method-assign]

    results = await factory.run()

    assert [project.mission.id for project in results] == [
        "mission-blocked",
        "mission-next",
    ]
    assert factory.queue == []
    assert factory._running is False
