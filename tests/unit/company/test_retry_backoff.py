import time

import pytest

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class _Runtime:
    async def generate(self, request):
        return ModelResponse(content="ok", model="test", provider="test")


def _factory():
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator, AgentExecutor(_Runtime()), AgentRegistry()
    )
    return ProjectFactory(orchestrator, controller, pipeline)


def test_retry_backoff_is_exponential_capped_and_persistable():
    factory = _factory()
    project = factory.enqueue(
        CompanyMission(name="Retry cooldown", objective="Use bounded backoff")
    )
    project.attempts = 1
    before = time.time()

    factory._apply_retry_backoff(project)

    assert before + 0.45 <= project.retry_not_before_epoch <= time.time() + 0.55
    project.attempts = 100
    factory._apply_retry_backoff(project)
    assert project.retry_not_before_epoch <= time.time() + 30.01
    assert project.retry_not_before_epoch > time.time() + 29


@pytest.mark.asyncio
async def test_delayed_retry_yields_to_another_ready_project():
    factory = _factory()
    delayed = factory.enqueue(
        CompanyMission(name="Cooling down", objective="Wait for retry cooldown")
    )
    ready = factory.enqueue(
        CompanyMission(name="Ready now", objective="Run without waiting")
    )
    delayed.retry_not_before_epoch = time.time() + 60

    result = await factory.run_next(max_stages=1, max_retries=0)

    assert result is ready
    assert delayed in factory.queue
    assert delayed.retry_not_before_epoch > time.time()