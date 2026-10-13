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

