"""Cross-cutting recovery regression scenarios spanning durable jobs and snapshots."""

import pytest
from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class FakeRuntime:
    async def generate(self, request):
        return ModelResponse(content="regression-safe", model="fake", provider="fake")


class MemoryJobStore:
    def __init__(self, jobs):
        self.jobs = {job.id: job for job in jobs}
        self.fail_save = False

    def get(self, mission_id):
        return self.jobs.get(mission_id)

    def list_all(self):
        return list(self.jobs.values())

    def save(self, job):
        if self.fail_save:
            raise OSError("injected durable job write failure")
        self.jobs[job.id] = job


class MemoryProjectStore:
    def __init__(self, pending=None):
        self.pending = list(pending or [])
        self.fail_save = False
        self.save_count = 0

    def load_pending(self):
        return list(self.pending)

    def save(self, project):
        if self.fail_save:
            raise OSError("injected project snapshot write failure")
        self.save_count += 1
        self.pending = [
            item for item in self.pending
            if item["mission"].id != project.mission.id
        ]
        self.pending.append({
            "mission": project.mission,
            "plan": project.plan.model_copy(deep=True),
            "status": project.status,
            "attempts": project.attempts,
            "stages_executed": project.stages_executed,
            "last_error": project.last_error,
            "retry_feedback": project.retry_feedback,
        })


def make_job(name, status=MissionJobStatus.QUEUED):
    mission = CompanyMission(name=name, objective=f"Recovery regression for {name}")
    return MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=status,
        message="persisted regression fixture",
        attempts=2,
    )


def make_factory(job_store, project_store=None):
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    return ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        store=project_store,
        job_store=job_store,
    )


@pytest.mark.parametrize(
    ("status", "expected_restored"),
    [
        (MissionJobStatus.QUEUED, 1),
        (MissionJobStatus.RUNNING, 1),
        (MissionJobStatus.COMPLETED, 0),
        (MissionJobStatus.FAILED, 0),
        (MissionJobStatus.BLOCKED, 0),
        (MissionJobStatus.CANCELLED, 0),
    ],
)
def test_restart_recovery_matrix_never_resurrects_terminal_jobs(status, expected_restored):
    job = make_job(f"status matrix {status.value}", status)
    if status == MissionJobStatus.RUNNING:
        job.plan.steps[0].status = "completed"
        job.plan.steps[1].status = "running"
        job.plan.steps[1].detail = "interrupted stage"
    jobs = MemoryJobStore([job])
    factory = make_factory(jobs)

    restored = factory.restore()

    assert restored == expected_restored
    assert len(factory.queue) == expected_restored
    if status == MissionJobStatus.RUNNING:
        recovered = jobs.get(job.id)
        assert recovered.status == MissionJobStatus.QUEUED
        assert recovered.plan.steps[0].status == "completed"
        assert recovered.plan.steps[1].status == "planned"
        assert recovered.plan.steps[1].detail is None
    if status in {MissionJobStatus.COMPLETED, MissionJobStatus.CANCELLED}:
        assert all(project.mission.id != job.id for project in factory.queue)


def test_repeated_restore_after_interrupted_stage_is_idempotent():
    job = make_job("repeat restart")
    job.status = MissionJobStatus.RUNNING
    job.plan.steps[0].status = "completed"
    job.plan.steps[1].status = "running"
    jobs = MemoryJobStore([job])
    factory = make_factory(jobs)

    assert factory.restore() == 1
    first_plan = factory.queue[0].plan.model_dump()
    assert factory.restore() == 0
    assert len(factory.queue) == 1
    assert factory.queue[0].plan.model_dump() == first_plan


def test_snapshot_write_failure_does_not_hide_durable_queued_job():
    job = make_job("snapshot failure")
    jobs = MemoryJobStore([job])
    projects = MemoryProjectStore()
    projects.fail_save = True
    factory = make_factory(jobs, projects)

    # The durable job is already QUEUED, so restore can safely rehydrate it
    # even when the redundant project snapshot cannot be refreshed.
    assert factory.restore() == 1
    assert [project.mission.id for project in factory.queue] == [job.id]


def test_durable_running_job_write_failure_does_not_publish_interrupted_work():
    job = make_job("durable failure", MissionJobStatus.RUNNING)
    job.plan.steps[0].status = "running"
    jobs = MemoryJobStore([job])
    jobs.fail_save = True
    factory = make_factory(jobs)

    assert factory.restore() == 0
    assert factory.queue == []
    assert jobs.get(job.id).status == MissionJobStatus.RUNNING


def test_restore_keeps_independent_missions_available_after_one_bad_snapshot():
    first = make_job("first broken snapshot")
    second = make_job("second recoverable snapshot")
    projects = MemoryProjectStore([
        {"mission": first.mission, "plan": first.plan, "status": "queued", "attempts": 0},
        {"mission": second.mission, "plan": second.plan, "status": "queued", "attempts": 0},
    ])
    original_save = projects.save

    def fail_first(project):
        if project.mission.id == first.id:
            raise OSError("injected single-mission snapshot failure")
        original_save(project)

    projects.save = fail_first
    factory = make_factory(MemoryJobStore([]), projects)

    assert factory.restore() == 2
    assert [project.mission.id for project in factory.queue] == [first.id, second.id]


def test_restore_never_duplicates_an_already_queued_mission():
    job = make_job("duplicate prevention")
    factory = make_factory(MemoryJobStore([job]))

    assert factory.restore() == 1
    assert factory.restore() == 0
    assert len([item for item in factory.queue if item.mission.id == job.id]) == 1
