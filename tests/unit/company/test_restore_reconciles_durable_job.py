from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.project_factory import ProjectFactory


def test_restore_reconciles_durable_running_job_and_preserves_completed_stages():
    mission = CompanyMission(
        name="Restart recovery",
        objective="Recover the in-flight stage without losing completed work",
    )
    plan = build_mission_plan(mission)
    plan.steps[0].status = "completed"
    plan.steps[0].detail = "Research completed"
    plan.steps[1].status = "running"
    plan.steps[1].detail = "Interrupted during implementation"
    project_data = {
        "mission": mission,
        "plan": plan,
        "status": "running",
        "stages_executed": 1,
        "attempts": 1,
        "last_error": None,
        "retry_feedback": None,
    }
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=MissionJobStatus.RUNNING,
        message="Factory attempt started",
        attempts=1,
    )

    class ProjectStore:
        def __init__(self):
            self.saved = []

        def save(self, project):
            self.saved.append(project)

        def load_pending(self):
            return [project_data]

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
    factory.queue = []
    factory._active_project = None

    assert factory.restore() == 1

    restored = factory.queue[0]
    recovered_job = factory.job_store.jobs[mission.id]
    assert restored.status == "queued"
    assert restored.plan.steps[0].status == "completed"
    assert restored.plan.steps[0].detail == "Research completed"
    assert restored.plan.steps[1].status == "planned"
    assert restored.plan.steps[1].detail is None
    assert recovered_job.status == MissionJobStatus.QUEUED
    assert recovered_job.plan.steps[0].status == "completed"
    assert recovered_job.plan.steps[1].status == "planned"
    assert "recovered after process restart" in recovered_job.message.lower()
