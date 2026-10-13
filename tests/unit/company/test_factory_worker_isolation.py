"""Regression tests for isolating factory missions from persistence failures."""

import pytest

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class SuccessfulRuntime:
    async def generate(self, request):
        return ModelResponse(
            content="stage completed",
            model="fake",
            provider="fake",
        )


@pytest.mark.asyncio
async def test_factory_continues_when_one_mission_snapshot_save_fails() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(SuccessfulRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)
    first = factory.enqueue(
        CompanyMission(name="Snapshot failure", objective="Fail one persistence write")
    )
    second = factory.enqueue(
        CompanyMission(name="Continue factory", objective="Complete the next mission")
    )

    original_save = factory._save
    failed_once = False

    def fail_first_save(project):
        nonlocal failed_once
        if project.mission.id == first.mission.id and not failed_once:
            failed_once = True
            raise OSError("temporary snapshot storage failure")
        original_save(project)

    factory._save = fail_first_save  # type: ignore[method-assign]

    results = await factory.run(max_projects=2, max_stages=12, max_retries=0)

    assert failed_once
    assert first.status == "blocked"
    assert "snapshot storage failure" in (first.last_error or "")
    assert second.status == "completed"
    assert results == [first, second]
    assert factory._running is False
    assert factory._active_project is None
