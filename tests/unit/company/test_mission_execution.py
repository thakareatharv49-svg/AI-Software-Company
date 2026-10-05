import pytest

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator


class FakeProvider:
    name = "fake"

    async def generate(self, request):
        return ModelResponse(
            content=f"completed: {request.prompt[:30]}",
            model="fake",
            provider=self.name,
        )


class FakeRuntime:
    def __init__(self):
        self.provider = FakeProvider()

    async def generate(self, request):
        return await self.provider.generate(request)


@pytest.mark.asyncio
async def test_execute_next_runs_agent_and_advances_stage() -> None:
    orchestrator = CompanyOrchestrator()
    mission = CompanyMission(name="Build X", objective="Create X")
    controller = MissionController(orchestrator)
    plan, _ = controller.start(mission)

    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )

    result = await pipeline.execute_next(mission, plan)

    assert result.success is True
    assert plan.steps[0].status == "completed"
    assert plan.steps[1].status == "planned"
    assert orchestrator.state.completed_tasks == 1
    assert orchestrator.state.current_task_id == f"task:{mission.id}:product"
    assert orchestrator.state.status.value == "running"
    assert any(
        event.event_type == "STAGE_COMPLETED"
        for event in orchestrator.events.list_events()
    )


@pytest.mark.asyncio
async def test_failed_stage_blocks_company() -> None:
    class FailingRuntime:
        async def generate(self, request):
            raise RuntimeError("model unavailable")

    orchestrator = CompanyOrchestrator()
    mission = CompanyMission(name="Build X", objective="Create X")
    controller = MissionController(orchestrator)
    plan, _ = controller.start(mission)

    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FailingRuntime()),
        AgentRegistry(),
    )

    result = await pipeline.execute_next(mission, plan)

    assert result.success is False
    assert plan.steps[0].status == "failed"
    assert orchestrator.state.status.value == "blocked"
    assert any(
        event.event_type == "STAGE_FAILED"
        for event in orchestrator.events.list_events()
    )
