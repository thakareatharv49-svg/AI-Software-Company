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


def test_restore_reconciles_running_job_when_project_snapshot_is_still_queued():
    mission = CompanyMission(
        name="Stale queued snapshot",
        objective="Recover a job whose durable status advanced before its project snapshot",
    )
    stale_plan = build_mission_plan(mission)
    latest_plan = build_mission_plan(mission)
    latest_plan.steps[0].status = "completed"
    latest_plan.steps[0].detail = "Research completed before crash"
    latest_plan.steps[1].status = "running"
    latest_plan.steps[1].detail = "Interrupted implementation"
    project_data = {
        "mission": mission,
        "plan": stale_plan,
        "status": "queued",
        "stages_executed": 0,
        "attempts": 0,
        "last_error": None,
        "retry_feedback": None,
    }
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=latest_plan,
        status=MissionJobStatus.RUNNING,
        message="Factory attempt started",
        attempts=2,
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
    assert restored.attempts == 2
    assert restored.plan.steps[0].status == "completed"
    assert restored.plan.steps[0].detail == "Research completed before crash"
    assert restored.plan.steps[1].status == "planned"
    assert restored.plan.steps[1].detail is None
    assert recovered_job.status == MissionJobStatus.QUEUED
    assert recovered_job.plan.steps[0].status == "completed"
    assert recovered_job.plan.steps[1].status == "planned"


def test_restore_prefers_newer_queued_job_plan_and_is_idempotent():
    mission = CompanyMission(
        name="Queued snapshot reconciliation",
        objective="Keep the newest durable queued progress after a crash",
    )
    stale_plan = build_mission_plan(mission)
    durable_plan = build_mission_plan(mission)
    durable_plan.steps[0].status = "completed"
    durable_plan.steps[0].detail = "Research preserved"
    project_data = {
        "mission": mission,
        "plan": stale_plan,
        "status": "queued",
        "stages_executed": 0,
        "attempts": 0,
        "last_error": None,
        "retry_feedback": None,
    }
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=durable_plan,
        status=MissionJobStatus.QUEUED,
        message="Paused and queued",
        attempts=2,
    )

    class ProjectStore:
        def __init__(self):
            self.saved = []

        def save(self, project):
            self.saved.append(project)

        def load_pending(self):
            return [project_data, project_data]

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
    assert len(factory.queue) == 1
    restored = factory.queue[0]
    assert restored.attempts == 2
    assert restored.plan.steps[0].status == "completed"
    assert restored.plan.steps[0].detail == "Research preserved"

    # A second restore must not duplicate the mission or reset its progress.
    assert factory.restore() == 0
    assert len(factory.queue) == 1
    assert factory.queue[0].plan.steps[0].status == "completed"
    assert factory.queue[0].attempts == 2



def test_restore_redacts_legacy_secrets_before_reusing_retry_feedback():
    mission = CompanyMission(
        name="Legacy diagnostic recovery",
        objective="Never pass persisted credentials back into the model",
    )
    plan = build_mission_plan(mission)
    plan.steps[0].status = "failed"
    plan.steps[0].detail = "Build failed: api_key=supersecret123456"
    project_data = {
        "mission": mission,
        "plan": plan,
        "status": "running",
        "stages_executed": 0,
        "attempts": 1,
        "last_error": None,
        "retry_feedback": None,
    }
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=MissionJobStatus.RUNNING,
        message="Interrupted before retry",
        attempts=1,
    )

    class ProjectStore:
        def save(self, project):
            pass

        def load_pending(self):
            return [project_data]

    class JobStore:
        def get(self, job_id):
            return job if job_id == mission.id else None

        def save(self, saved):
            pass

    factory = object.__new__(ProjectFactory)
    factory.store = ProjectStore()
    factory.job_store = JobStore()
    factory.queue = []
    factory._active_project = None

    assert factory.restore() == 1
    feedback = factory.queue[0].retry_feedback
    assert feedback is not None
    assert "supersecret123456" not in feedback
    assert "api_key=[REDACTED]" in feedback
