from datetime import UTC, datetime
from types import SimpleNamespace

from src.company.persistence import MissionJobStore


def test_get_quarantines_malformed_job_and_returns_none(monkeypatch, caplog):
    import src.company.persistence as persistence

    now = datetime.now(UTC)
    malformed = SimpleNamespace(
        id="broken-job",
        mission={"unexpected": "value"},
        plan={"steps": "invalid"},
        status="queued",
        message="old message",
        workspace_id=None,
        attempts=0,
        created_at=now,
        updated_at=now,
    )

    class FakeSession:
        def __init__(self, _engine):
            self.commits = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, _model, job_id):
            assert job_id == "broken-job"
            return malformed

        def commit(self):
            self.commits += 1

    sessions = []

    def fake_session(engine):
        session = FakeSession(engine)
        sessions.append(session)
        return session

    monkeypatch.setattr(persistence, "Session", fake_session)
    store = MissionJobStore.__new__(MissionJobStore)
    store._engine = object()

    with caplog.at_level("ERROR"):
        result = store.get("broken-job")

    assert result is None
    assert malformed.status == "blocked"
    assert malformed.message == "Blocked because the persisted mission snapshot is invalid."
    assert malformed.updated_at >= now
    assert "Quarantining malformed mission-job snapshot during lookup" in caplog.text
    assert "unexpected" not in caplog.text
    assert sessions[0].commits == 1
