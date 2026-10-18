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


@pytest.mark.asyncio
async def test_cancelling_factory_run_requeues_active_mission_and_preserves_completed_stages():
    started = asyncio.Event()
    never_finish = asyncio.Event()

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

    class WaitingRunner:
        async def run(self, mission, plan, on_progress=None):
            plan.steps[0].status = "completed"
            plan.steps[0].detail = "Research finished"
            plan.steps[1].status = "running"
            if on_progress is not None:
                on_progress(plan)
            started.set()
            await never_finish.wait()

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
        autonomous_runner=WaitingRunner(),
    )
    project = factory.enqueue(
        CompanyMission(name="Interruptible", objective="Resume safely after shutdown")
    )

    task = asyncio.create_task(factory.run(max_projects=1))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert project.status == "queued"
    assert len(factory.queue) == 1
    assert factory.queue[0] is project
    assert project.plan.steps[0].status == "completed"
    assert project.plan.steps[0].detail == "Research finished"
    assert project.plan.steps[1].status == "planned"
    assert project.plan.steps[1].detail is None
    assert jobs.jobs[project.mission.id].status == MissionJobStatus.QUEUED
    assert jobs.jobs[project.mission.id].plan.steps[0].status == "completed"
    assert factory._active_project is None
    assert factory._running is False


@pytest.mark.asyncio
async def test_cancellation_does_not_requeue_when_recovery_persistence_fails(caplog):
    started = asyncio.Event()
    never_finish = asyncio.Event()

    class JobStore:
        def __init__(self):
            self.jobs = {}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, job):
            self.jobs[job.id] = job

    class FailingProjectStore:
        def __init__(self):
            self.saves = 0

        def save(self, project):
            self.saves += 1
            if self.saves >= 3:
                raise OSError("snapshot store unavailable")

        def load_pending(self):
            return []

    class WaitingRunner:
        async def run(self, mission, plan, on_progress=None):
            started.set()
            await never_finish.wait()

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
        store=FailingProjectStore(),
        job_store=jobs,
        autonomous_runner=WaitingRunner(),
    )
    project = factory.enqueue(
        CompanyMission(name="Persistence failure", objective="Avoid duplicate retries")
    )

    task = asyncio.create_task(factory.run(max_projects=1))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert factory.queue == []
    assert factory._active_project is None
    assert project.status == "queued"
    assert "recovery persistence failed" in project.last_error
    assert "leaving it out of the in-process queue" in caplog.text
