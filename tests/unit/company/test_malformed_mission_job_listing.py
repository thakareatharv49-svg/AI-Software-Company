from datetime import UTC, datetime
from types import SimpleNamespace

from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission


def test_list_all_quarantines_malformed_job_and_returns_healthy_jobs(monkeypatch, caplog):
    import src.company.persistence as persistence

    now = datetime.now(UTC)
    healthy_mission = CompanyMission(name="Healthy job", objective="Still visible")
    healthy_plan = build_mission_plan(healthy_mission)
    malformed = SimpleNamespace(
        id="malformed-job",
        mission={"unexpected": "shape"},
        plan={"steps": "not-a-list"},
        status="queued",
        message="bad record",
        workspace_id=None,
        attempts=0,
        created_at=now,
        updated_at=now,
    )
    healthy = SimpleNamespace(
        id=healthy_mission.id,
        mission=healthy_mission.model_dump(mode="json"),
        plan=healthy_plan.model_dump(mode="json"),
        status="queued",
        message="waiting",
        workspace_id=None,
        attempts=1,
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
        jobs = store.list_all()

    assert [job.id for job in jobs] == [healthy_mission.id]
    assert malformed.status == "blocked"
    assert malformed.message == "Blocked because the persisted mission snapshot is invalid."
    assert malformed.updated_at >= now
    assert "Quarantining malformed mission-job snapshot" in caplog.text
    assert "unexpected" not in caplog.text
    assert sessions[0].commits == 1
