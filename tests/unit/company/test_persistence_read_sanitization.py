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


def test_mission_job_list_rewrites_unsafe_legacy_fields(monkeypatch) -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace

    import src.company.persistence as persistence
    from src.company.mission_jobs import MissionJobStatus

    mission = CompanyMission(name="Legacy", objective="Safe objective")
    plan = build_mission_plan(mission)
    unsafe_mission = mission.model_dump(mode="json")
    unsafe_mission["objective"] = "api_key=legacyReadSecret123456 " + ("legacy " * 1500)
    unsafe_plan = plan.model_dump(mode="json")
    unsafe_plan["steps"][0]["detail"] = "password=legacyPlanSecret123456 " + ("detail " * 700)
    now = datetime.now(UTC)
    row = SimpleNamespace(
        id=mission.id,
        mission=unsafe_mission,
        plan=unsafe_plan,
        status=MissionJobStatus.QUEUED.value,
        message="token=legacyMessageSecret123456 " + ("message " * 700),
        workspace_id="workspace-123",
        attempts=-4,
        created_at=now,
        updated_at=now,
    )

    class FakeScalars:
        def all(self):
            return [row]

    class FakeSession:
        def __init__(self, _engine):
            self.commits = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def scalars(self, _statement):
            return FakeScalars()

        def commit(self):
            self.commits += 1

    sessions = []

    def fake_session(engine):
        session = FakeSession(engine)
        sessions.append(session)
        return session

    monkeypatch.setattr(persistence, "Session", fake_session)
    store = persistence.MissionJobStore.__new__(persistence.MissionJobStore)
    store._engine = object()

    jobs = store.list_all()

    assert len(jobs) == 1
    assert "legacyReadSecret123456" not in jobs[0].mission.objective
    assert "legacyPlanSecret123456" not in (jobs[0].plan.steps[0].detail or "")
    assert "legacyMessageSecret123456" not in jobs[0].message
    assert jobs[0].attempts == 0
    assert jobs[0].workspace_id == "workspace-123"
    assert "legacyReadSecret123456" not in row.mission["objective"]
    assert "legacyPlanSecret123456" not in row.plan["steps"][0]["detail"]
    assert "legacyMessageSecret123456" not in row.message
    assert row.attempts == 0
    assert sessions[0].commits == 1


def test_pending_project_restore_rewrites_unsafe_legacy_snapshot(monkeypatch) -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace

    import src.company.persistence as persistence

    mission = CompanyMission(name="Pending legacy", objective="Safe objective")
    plan = build_mission_plan(mission)
    plan.steps[0].status = "running"
    plan.steps[0].detail = "password=legacySnapshotSecret123456 " + ("detail " * 700)
    unsafe_mission = mission.model_dump(mode="json")
    unsafe_mission["objective"] = "api_key=legacySnapshotMissionSecret123456 " + ("objective " * 900)
    unsafe_plan = plan.model_dump(mode="json")
    now = datetime.now(UTC)
    row = SimpleNamespace(
        id=mission.id,
        mission=unsafe_mission,
        plan=unsafe_plan,
        status="running",
        stages_executed=-2,
        attempts=-3,
        updated_at=now,
    )

    class FakeScalars:
        def all(self):
            return [row]

    class FakeSession:
        def __init__(self, _engine):
            self.commits = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def scalars(self, _statement):
            return FakeScalars()

        def commit(self):
            self.commits += 1

    sessions = []

    def fake_session(engine):
        session = FakeSession(engine)
        sessions.append(session)
        return session

    monkeypatch.setattr(persistence, "Session", fake_session)
    store = persistence.ProjectStore.__new__(persistence.ProjectStore)
    store._engine = object()

    pending = store.load_pending()

    assert len(pending) == 1
    assert pending[0]["status"] == "queued"
    assert pending[0]["plan"].steps[0].status == "planned"
    assert "legacySnapshotMissionSecret123456" not in pending[0]["mission"].objective
    assert "legacySnapshotSecret123456" not in (pending[0]["plan"].steps[0].detail or "")
    assert pending[0]["stages_executed"] == 0
    assert pending[0]["attempts"] == 0
    assert row.status == "queued"
    assert "legacySnapshotMissionSecret123456" not in row.mission["objective"]
    assert "legacySnapshotSecret123456" not in (row.plan["steps"][0]["detail"] or "")
    assert row.stages_executed == 0
    assert row.attempts == 0
    assert sessions[0].commits == 1


def test_pending_project_restore_skips_malformed_snapshot_and_keeps_healthy_rows(monkeypatch, caplog) -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace

    import src.company.persistence as persistence

    healthy_mission = CompanyMission(name="Healthy pending", objective="Continue after corrupt row")
    healthy_plan = build_mission_plan(healthy_mission)
    now = datetime.now(UTC)
    malformed = SimpleNamespace(
        id="malformed-snapshot",
        mission={"unexpected": "shape"},
        plan={"steps": "not-a-list"},
        status="queued",
        stages_executed=0,
        attempts=0,
        updated_at=now,
    )
    healthy = SimpleNamespace(
        id=healthy_mission.id,
        mission=healthy_mission.model_dump(mode="json"),
        plan=healthy_plan.model_dump(mode="json"),
        status="queued",
        stages_executed=1,
        attempts=2,
        updated_at=now,
    )

    class FakeScalars:
        def all(self):
            return [malformed, healthy]

    class FakeSession:
        def __init__(self, _engine):
            self.commits = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def scalars(self, _statement):
            return FakeScalars()

        def commit(self):
            self.commits += 1

    sessions = []

    def fake_session(engine):
        session = FakeSession(engine)
        sessions.append(session)
        return session

    monkeypatch.setattr(persistence, "Session", fake_session)
    store = persistence.ProjectStore.__new__(persistence.ProjectStore)
    store._engine = object()

    with caplog.at_level("ERROR"):
        pending = store.load_pending()

    assert len(pending) == 1
    assert pending[0]["mission"].id == healthy_mission.id
    assert pending[0]["status"] == "queued"
    assert pending[0]["stages_executed"] == 1
    assert pending[0]["attempts"] == 2
    assert "Quarantining malformed pending factory snapshot" in caplog.text
    assert "unexpected" not in caplog.text
    assert malformed.status == "blocked"
    assert malformed.updated_at >= now
    assert sessions[0].commits == 1
