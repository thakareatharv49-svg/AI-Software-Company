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
        return ModelResponse(
            content="stage completed",
            model="fake",
            provider="fake",
        )


@pytest.mark.asyncio
async def test_factory_runs_projects_sequentially() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)

    first = factory.enqueue(CompanyMission(name="One", objective="Build one"))
    second = factory.enqueue(CompanyMission(name="Two", objective="Build two"))

    results = await factory.run(max_projects=2, max_stages=12)

    assert first.status == "completed"
    assert second.status == "completed"
    assert len(results) == 2
    assert orchestrator.state.status.value == "stopped"
    assert orchestrator.state.completed_projects == 2
    assert orchestrator.state.completed_tasks == 24


@pytest.mark.asyncio
async def test_factory_stops_after_blocked_project() -> None:
    class FailingRuntime:
        async def generate(self, request):
            raise RuntimeError("model unavailable")

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FailingRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)

    project = factory.enqueue(CompanyMission(name="Blocked", objective="Fail safely"))
    queued = factory.enqueue(CompanyMission(name="Later", objective="Should remain queued"))

    results = await factory.run(max_projects=2)

    assert project.status == "blocked"
    assert queued.status == "queued"
    assert len(results) == 1
    assert orchestrator.state.status.value == "blocked"


@pytest.mark.asyncio
async def test_factory_can_pause_and_resume_a_project() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)
    project = factory.enqueue(CompanyMission(name="Resume", objective="Build resume-safe project"))

    paused = await factory.run_next(max_stages=2)

    assert paused is project
    assert project.status == "queued"
    assert project.stages_executed == 2
    assert len(factory.queue) == 1
    assert project.plan.steps[0].status == "completed"
    assert project.plan.steps[2].status == "planned"

    resumed = await factory.run_next(max_stages=10)

    assert resumed is project
    assert project.status == "completed"
    assert project.stages_executed == 12
    assert len(factory.queue) == 0
