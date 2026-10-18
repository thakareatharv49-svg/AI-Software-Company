import pytest

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_jobs import MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class _Runtime:
    async def generate(self, request):
        return ModelResponse(content="ok", model="test", provider="test")


class _JobStore:
    def __init__(self):
        self.jobs = {}

    def get(self, job_id):
        return self.jobs.get(job_id)

    def save(self, job):
        self.jobs[job.id] = job


def _factory(job_store=None):
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator, AgentExecutor(_Runtime()), AgentRegistry()
    )
    return ProjectFactory(orchestrator, controller, pipeline, job_store=job_store)


@pytest.mark.asyncio
async def test_run_next_rejects_overlapping_execution_without_consuming_queue():
    factory = _factory()
    project = factory.enqueue(CompanyMission(name="Active", objective="Build once"))
    factory._active_project = project

    with pytest.raises(RuntimeError, match="Factory execution is already active"):
        await factory.run_next()

    assert factory.queue == [project]
    assert project.attempts == 0


@pytest.mark.asyncio
async def test_run_next_discards_stale_queue_entry_for_nonqueued_durable_job():
    jobs = _JobStore()
    factory = _factory(job_store=jobs)
    project = factory.enqueue(CompanyMission(name="Already done", objective="Do not repeat"))
    jobs.jobs[project.mission.id] = jobs.jobs[project.mission.id].model_copy(
        update={"status": MissionJobStatus.COMPLETED}
    )

    result = await factory.run_next()

    assert result is None
    assert factory.queue == []
    assert project.attempts == 0
    assert jobs.jobs[project.mission.id].status == MissionJobStatus.COMPLETED