import pytest

from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.project_factory import FactoryProject, ProjectFactory


def _factory_with_stores(job_store, project_store):
    factory = object.__new__(ProjectFactory)
    factory.job_store = job_store
    factory.store = project_store
    return factory


def test_progress_persists_authoritative_job_before_project_snapshot():
    mission = CompanyMission(name="Progress order", objective="Keep stage state consistent")
    plan = build_mission_plan(mission)
    plan.steps[0].status = "completed"
    plan.steps[0].detail = "Research complete"
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=MissionJobStatus.RUNNING,
        message="Working",
    )
    events = []

    class JobStore:
        def get(self, job_id):
            return job if job_id == mission.id else None

        def save(self, saved):
            nonlocal job
            job = saved
            events.append(("job", saved.plan.steps[0].status))

    class ProjectStore:
        def save(self, saved):
            events.append(("snapshot", saved.plan.steps[0].status))

    factory = _factory_with_stores(JobStore(), ProjectStore())
    project = FactoryProject(mission=mission, plan=plan, status="running")

    factory._persist_plan_progress(project)

    assert events == [("job", "completed"), ("snapshot", "completed")]
    assert job.plan.steps[0].detail == "Research complete"


def test_failed_authoritative_progress_write_does_not_publish_new_snapshot():
    mission = CompanyMission(name="Progress failure", objective="Avoid inconsistent state")
    plan = build_mission_plan(mission)
    plan.steps[0].status = "completed"
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=MissionJobStatus.RUNNING,
        message="Working",
    )

    class JobStore:
        def get(self, job_id):
            return job if job_id == mission.id else None

        def save(self, saved):
            raise OSError("durable job store unavailable")

    class ProjectStore:
        def __init__(self):
            self.saved = []

        def save(self, saved):
            self.saved.append(saved)

    snapshots = ProjectStore()
    factory = _factory_with_stores(JobStore(), snapshots)
    project = FactoryProject(mission=mission, plan=plan, status="running")

    with pytest.raises(OSError, match="durable job store unavailable"):
        factory._persist_plan_progress(project)

    assert snapshots.saved == []
