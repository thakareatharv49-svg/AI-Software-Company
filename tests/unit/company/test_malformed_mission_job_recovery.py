from datetime import UTC, datetime
from types import SimpleNamespace

from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission


def test_recover_running_jobs_skips_malformed_row_and_recovers_healthy_row(monkeypatch, caplog):
    import src.company.persistence as persistence

    healthy_mission = CompanyMission(name="Healthy job", objective="Recover after corrupt job")
    healthy_plan = build_mission_plan(healthy_mission)
    healthy_plan.steps[0].status = "running"
    now = datetime.now(UTC)
    malformed = SimpleNamespace(
        id="malformed-job",
        mission={"unexpected": "shape"},
        plan={"steps": "not-a-list"},
        status="running",
        message="interrupted",
        workspace_id=None,
        attempts=0,
        created_at=now,
        updated_at=now,
    )
    healthy = SimpleNamespace(
        id=healthy_mission.id,
        mission=healthy_mission.model_dump(mode="json"),
        plan=healthy_plan.model_dump(mode="json"),
        status="running",
        message="interrupted",
        workspace_id="workspace-healthy",
        attempts=2,
        created_at=now,
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
    store = persistence.MissionJobStore.__new__(persistence.MissionJobStore)
    store._engine = object()

    with caplog.at_level("ERROR"):
        recovered = store.recover_running()

    assert len(recovered) == 1
    assert recovered[0].id == healthy_mission.id
    assert recovered[0].status.value == "queued"
    assert recovered[0].workspace_id == "workspace-healthy"
    assert recovered[0].plan.steps[0].status == "planned"
    assert healthy.status == "queued"
    assert "Skipping malformed running mission-job snapshot" in caplog.text
    assert "unexpected" not in caplog.text
    assert sessions[0].commits == 1
