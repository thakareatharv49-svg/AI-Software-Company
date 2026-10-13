from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission
from src.company.persistence import _safe_mission, _safe_plan


def test_persisted_mission_text_is_bounded_before_use() -> None:
    mission = CompanyMission(name="n" * 900, objective="o" * 12000, constraints=["c" * 3000])
    safe = _safe_mission(mission)

    assert len(safe.name) == 500
    assert len(safe.objective) == 8000
    assert len(safe.constraints[0]) == 2000


def test_persisted_plan_text_is_bounded_without_losing_progress() -> None:
    mission = CompanyMission(name="Restore", objective="Restore a plan safely")
    plan = build_mission_plan(mission)
    plan.steps[0].status = "completed"
    plan.steps[0].detail = "d" * 6000
    plan.engineering_tasks[0].requirement = "r" * 6000

    safe = _safe_plan(plan)

    assert safe.steps[0].status == "completed"
    assert len(safe.steps[0].detail) == 4000
    assert len(safe.engineering_tasks[0].requirement) == 4000


def test_recovered_job_is_normalized_before_being_returned_or_rewritten() -> None:
    from src.company.mission_jobs import MissionJob, MissionJobStatus
    from src.company.persistence import _safe_job

    mission = CompanyMission(name="Recovered", objective="Recover safely")
    plan = build_mission_plan(mission)
    unsafe_mission = mission.model_copy(update={
        "objective": "api_key=recoverySecret123456 " + ("legacy " * 1500),
    })
    unsafe_plan = plan.model_copy(deep=True)
    unsafe_plan.steps[0].detail = "password=recoveryPlanSecret123456 " + ("detail " * 700)
    unsafe = MissionJob(
        id=mission.id,
        mission=unsafe_mission,
        plan=unsafe_plan,
        status=MissionJobStatus.RUNNING,
        message="token=recoveryMessageSecret123456 " + ("message " * 700),
        attempts=-3,
    )

    safe = _safe_job(unsafe)

    assert "recoverySecret123456" not in safe.mission.objective
    assert len(safe.mission.objective) <= 8000
    assert "recoveryPlanSecret123456" not in (safe.plan.steps[0].detail or "")
    assert "recoveryMessageSecret123456" not in safe.message
    assert len(safe.message) <= 4000
    assert safe.attempts == 0


def test_mission_job_list_preserves_workspace_ownership(monkeypatch) -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace

    import src.company.persistence as persistence
    from src.company.mission_jobs import MissionJobStatus

    mission = CompanyMission(name="Workspace mission", objective="Keep workspace scope")
    plan = build_mission_plan(mission)
    now = datetime.now(UTC)
    row = SimpleNamespace(
        id=mission.id,
        mission=mission.model_dump(mode="json"),
        plan=plan.model_dump(mode="json"),
        status=MissionJobStatus.QUEUED.value,
        message="queued",
        workspace_id="workspace-owned-123",
        attempts=0,
        created_at=now,
        updated_at=now,
    )

    class FakeScalars:
        def all(self):
            return [row]

    class FakeSession:
        def __init__(self, _engine):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def scalars(self, _statement):
            return FakeScalars()

    monkeypatch.setattr(persistence, "Session", FakeSession)
    store = persistence.MissionJobStore.__new__(persistence.MissionJobStore)
    store._engine = object()

    jobs = store.list_all()

    assert len(jobs) == 1
    assert jobs[0].workspace_id == "workspace-owned-123"
