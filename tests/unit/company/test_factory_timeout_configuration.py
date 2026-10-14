import math

import pytest

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class FakeRuntime:
    async def generate(self, request):
        return ModelResponse(content="stage completed", model="fake", provider="fake")


@pytest.mark.parametrize(
    "timeout",
    [0, -1, math.inf, -math.inf, math.nan, None, "10", True, False],
)
@pytest.mark.asyncio
async def test_invalid_execution_timeout_does_not_dequeue_mission(timeout: float) -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        execution_timeout_seconds=timeout,
    )
    project = factory.enqueue(
        CompanyMission(name="Timeout validation", objective="Preserve queue on invalid timeout")
    )

    with pytest.raises(
        ValueError,
        match="execution_timeout_seconds must be a finite positive number",
    ):
        await factory.run_next()

    assert factory.queue == [project]
    assert project.status == "queued"
    assert project.attempts == 0


@pytest.mark.parametrize("max_stages", [-1, 1.5, "2", True, False])
@pytest.mark.asyncio
async def test_invalid_stage_budget_does_not_dequeue_mission(max_stages) -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)
    project = factory.enqueue(
        CompanyMission(
            name="Stage budget validation",
            objective="Preserve queue on invalid stage budget",
        )
    )

    with pytest.raises(
        ValueError,
        match="max_stages must be a non-negative integer or None",
    ):
        await factory.run_next(max_stages=max_stages)

    assert factory.queue == [project]
    assert project.status == "queued"
    assert project.attempts == 0

@pytest.mark.parametrize("max_retries", [-1, 1.5, "2", None, True, False])
@pytest.mark.asyncio
async def test_invalid_retry_budget_does_not_dequeue_mission(max_retries) -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)
    project = factory.enqueue(
        CompanyMission(
            name="Retry budget validation",
            objective="Preserve queue on invalid retry budget",
        )
    )

    with pytest.raises(
        ValueError,
        match="max_retries must be a non-negative integer",
    ):
        await factory.run_next(max_retries=max_retries)

    assert factory.queue == [project]
    assert project.status == "queued"
    assert project.attempts == 0
