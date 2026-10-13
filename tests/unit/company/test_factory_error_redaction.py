from types import SimpleNamespace

from src.company.models.contracts import CompanyMission
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.project_factory import FactoryProject, ProjectFactory
from src.company.mission_controller.planner import build_mission_plan


def test_safe_error_detail_redacts_secrets_and_bounds_text():
    secret = "ghp_" + "T" * 32
    detail = ProjectFactory._safe_error_detail(
        f"RuntimeError: password=super-secret token={secret} " + ("x" * 5000)
    )

    assert "super-secret" not in detail
    assert secret not in detail
    assert "[REDACTED_TOKEN]" in detail
    assert len(detail) <= 4000



def test_retry_feedback_is_redacted_before_being_reused():
    mission = CompanyMission(
        name="Retry secret safety",
        objective="Do not echo credentials into the next model prompt",
    )
    project = FactoryProject(
        mission=mission,
        plan=build_mission_plan(mission),
        last_error="Build failed: api_key=supersecret123456",
    )
    factory = object.__new__(ProjectFactory)
    factory.orchestrator = SimpleNamespace(stop=lambda: None)
    factory._last_autonomous_result = None

    factory._reset_for_retry(project, reset_completed=True)

    assert project.retry_feedback is not None
    assert "supersecret123456" not in project.retry_feedback
    assert "api_key=[REDACTED]" in project.retry_feedback
    assert project.last_error is None



def test_manual_retry_feedback_is_redacted_before_being_reused():
    mission = CompanyMission(
        name="Manual retry secret safety",
        objective="Do not echo credentials from failed stages into the next model prompt",
    )
    plan = build_mission_plan(mission)
    failed_step = plan.steps[0]
    failed_step.status = "failed"
    failed_step.detail = "Build failed: api_key=supersecret123456"
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=MissionJobStatus.BLOCKED,
        message="blocked",
        attempts=1,
    )

    class JobStore:
        def get(self, _mission_id):
            return job

        def save(self, _job):
            pass

    class Store:
        def save(self, _project):
            pass

    class Audit:
        def append(self, _entry):
            pass

    factory = object.__new__(ProjectFactory)
    factory.job_store = JobStore()
    factory.store = Store()
    factory.audit_store = Audit()
    factory.queue = []
    factory._running = False
    factory.orchestrator = SimpleNamespace(
        events=SimpleNamespace(publish=lambda _event: None)
    )

    factory.retry(mission.id)
    project = factory.queue[0]

    assert project.retry_feedback is not None
    assert "supersecret123456" not in project.retry_feedback
    assert "api_key=[REDACTED]" in project.retry_feedback

def test_revision_feedback_is_redacted_before_persistence_and_audit():
    mission = CompanyMission(
        name="Revision secret safety",
        objective="Build a safe product using api_key=legacysecret123456",
    )
    plan = build_mission_plan(mission)
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=MissionJobStatus.COMPLETED,
        message="completed",
        attempts=1,
    )
    saved_jobs = []
    saved_projects = []
    audit_entries = []

    class JobStore:
        def get(self, _mission_id):
            return job

        def save(self, saved_job):
            saved_jobs.append(saved_job)

    class Store:
        def save(self, project):
            saved_projects.append(project)

    class Audit:
        def append(self, entry):
            audit_entries.append(entry)

    factory = object.__new__(ProjectFactory)
    factory.job_store = JobStore()
    factory.store = Store()
    factory.audit_store = Audit()
    factory.queue = []
    factory._running = False
    factory._last_autonomous_result = object()
    factory.orchestrator = SimpleNamespace(
        stop=lambda: None,
        events=SimpleNamespace(publish=lambda _event: None),
    )

    factory.revise(mission.id, "Please use api_key=supersecret123456 for the integration")

    revised_job = saved_jobs[-1]
    assert "supersecret123456" not in revised_job.mission.objective
    assert "legacysecret123456" not in revised_job.mission.objective
    assert "api_key=[REDACTED]" in revised_job.mission.objective
    assert "supersecret123456" not in audit_entries[-1].metadata["feedback"]
    assert "api_key=[REDACTED]" in audit_entries[-1].metadata["feedback"]


def test_enqueue_redacts_secrets_from_mission_fields_before_persistence_and_planning():
    mission = CompanyMission(
        name="Budget app api_key=namesecret123456",
        objective="Build a budget app with password=objectivesecret123456",
        constraints=["Use database_url=constraintsecret123456 only in local config"],
    )
    saved_jobs = []

    class JobStore:
        def get(self, _mission_id):
            return None

        def save(self, job):
            saved_jobs.append(job)

    class Store:
        def save(self, _project):
            pass

    class Audit:
        def append(self, _entry):
            pass

    factory = object.__new__(ProjectFactory)
    factory.job_store = JobStore()
    factory.store = Store()
    factory.audit_store = Audit()
    factory.queue = []
    factory._running = False
    factory.orchestrator = SimpleNamespace(
        events=SimpleNamespace(publish=lambda _event: None)
    )

    project = factory.enqueue(mission)
    persisted = saved_jobs[-1]

    for secret in ("namesecret123456", "objectivesecret123456", "constraintsecret123456"):
        assert secret not in persisted.mission.name
        assert secret not in persisted.mission.objective
        assert secret not in " ".join(persisted.mission.constraints)
        assert secret not in persisted.plan.objective
        assert secret not in " ".join(persisted.plan.constraints)
        assert secret not in " ".join(persisted.plan.acceptance_criteria)

    assert project.mission.name == persisted.mission.name
    assert "api_key=[REDACTED]" in persisted.mission.name
    assert "password=[REDACTED]" in persisted.mission.objective
    assert "database_url=[REDACTED]" in persisted.mission.constraints[0]
