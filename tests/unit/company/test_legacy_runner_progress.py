import asyncio

import pytest

from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.models.contracts import CompanyMission
from src.company.mission_jobs import MissionJobStatus
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class FakeRuntime:
    async def generate(self, request):
        raise AssertionError("The autonomous runner owns this test")


class JobStore:
    def __init__(self):
        self.jobs = {}

    def get(self, job_id):
        return self.jobs.get(job_id)

    def save(self, job):
        self.jobs[job.id] = job


class ProjectStore:
    def save(self, project):
        pass

    def load_pending(self):
        return []


@pytest.mark.asyncio
async def test_legacy_runner_persists_execution_progress_without_callback():
    started = asyncio.Event()
    never_finish = asyncio.Event()

    class LegacyRunner:
        # Deliberately lacks on_progress to model an older/custom adapter.
        async def run(self, mission, plan):
            started.set()
            await never_finish.wait()
            return type("Result", (), {"pipeline": object(), "stages": []})()

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    jobs = JobStore()
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        store=ProjectStore(),
        job_store=jobs,
        autonomous_runner=LegacyRunner(),
    )
    project = factory.enqueue(
        CompanyMission(
            name="Legacy progress",
            objective="Expose meaningful progress while the adapter runs",
        )
    )

    task = asyncio.create_task(factory.run(max_projects=1))
    await asyncio.wait_for(started.wait(), timeout=2)

    execution_step = next(
        step for step in project.plan.steps if step.stage.value == "execution"
    )
    assert execution_step.status == "running"
    assert "detailed stage telemetry is unavailable" in execution_step.detail
    assert jobs.jobs[project.mission.id].status == MissionJobStatus.RUNNING
    persisted_step = next(
        step
        for step in jobs.jobs[project.mission.id].plan.steps
        if step.stage.value == "execution"
    )
    assert persisted_step.status == "running"

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
