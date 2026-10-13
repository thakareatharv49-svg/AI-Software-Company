from types import SimpleNamespace

import pytest

from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.project_factory import ProjectFactory


def test_enqueue_preserves_existing_durable_queued_progress_when_snapshot_is_missing():
    mission = CompanyMission(
        name="Recover queued mission",
        objective="Resume the existing durable plan without losing progress",
    )
    plan = build_mission_plan(mission)
    plan.steps[0].status = "completed"
    plan.steps[0].detail = "Research already completed"
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=MissionJobStatus.QUEUED,
        message="Paused and queued",
        attempts=3,
    )

    class ProjectStore:
        def __init__(self):
            self.saved = []

        def save(self, project):
            self.saved.append(project)

    class JobStore:
        def __init__(self):
            self.jobs = {mission.id: job}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, saved):
            self.jobs[saved.id] = saved

    factory = object.__new__(ProjectFactory)
    factory.store = ProjectStore()
    factory.job_store = JobStore()
    factory.audit_store = None
    factory.queue = []
    factory.orchestrator = SimpleNamespace(
        events=SimpleNamespace(publish=lambda event: None)
    )

    project = factory.enqueue(mission)

    assert project.plan.steps[0].status == "completed"
    assert project.plan.steps[0].detail == "Research already completed"
    assert project.attempts == 3
    assert factory.job_store.jobs[mission.id].plan.steps[0].status == "completed"
    assert len(factory.queue) == 1
    assert len(factory.store.saved) == 1



def test_enqueue_rejects_durable_running_mission_until_restore_recovers_it():
    mission = CompanyMission(
        name="Interrupted mission",
        objective="Do not replace a running durable plan with a fresh plan",
    )
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=MissionJobStatus.RUNNING,
        message="Worker was running",
        attempts=1,
    )

    class JobStore:
        def get(self, job_id):
            return job if job_id == mission.id else None

        def save(self, saved):
            raise AssertionError("enqueue must not mutate a running durable job")

    factory = object.__new__(ProjectFactory)
    factory.job_store = JobStore()
    factory.queue = []
    factory._running = False

    with pytest.raises(ValueError, match="recover it before re-enqueueing"):
        factory.enqueue(mission)

    assert factory.queue == []
