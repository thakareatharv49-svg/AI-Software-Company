from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.project_factory import FactoryProject, ProjectFactory


def test_remove_missions_cancels_durable_queued_job():
    mission = CompanyMission(name="Removed", objective="Do not leave stale queued state")
    plan = build_mission_plan(mission)
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=MissionJobStatus.QUEUED,
        message="Project queued",
    )

    class JobStore:
        def __init__(self):
            self.jobs = {mission.id: job}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, saved):
            self.jobs[saved.id] = saved

    class ProjectStore:
        def save(self, project):
            pass

        def load_pending(self):
            return []

    factory = object.__new__(ProjectFactory)
    factory._active_project = None
    factory.queue = [FactoryProject(mission=mission, plan=plan)]
    factory.store = ProjectStore()
    factory.job_store = JobStore()
    factory.audit_store = None
    factory.orchestrator = type(
        "Orchestrator",
        (),
        {"events": type("Events", (), {"publish": lambda self, event: None})()},
    )()

    factory.remove_missions({mission.id})

    assert factory.queue == []
    assert factory.job_store.jobs[mission.id].status == MissionJobStatus.CANCELLED
    assert "removed from queue" in factory.job_store.jobs[mission.id].message.lower()
