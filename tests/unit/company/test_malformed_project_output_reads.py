from datetime import UTC, datetime
from types import SimpleNamespace

from src.company.persistence import ProjectOutputStore


def test_get_for_mission_quarantines_malformed_output_and_keeps_healthy_outputs(monkeypatch, caplog):
    import src.company.persistence as persistence

    now = datetime.now(UTC)
    malformed = SimpleNamespace(
        id="broken-output",
        mission_id="mission-1",
        project_id="project-broken",
        name=None,
        status="ready",
        output_type="factory_project",
        repository=None,
        github_message="old message",
        memory_id=None,
        created_at=now,
        updated_at=now,
    )
    healthy = SimpleNamespace(
        id="healthy-output",
        mission_id="mission-1",
        project_id="project-good",
        name="Healthy product",
        status="ready",
        output_type="factory_project",
        repository="https://github.com/example/product",
        github_message="published",
        memory_id=None,
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
    store = ProjectOutputStore.__new__(ProjectOutputStore)
    store._engine = object()

    with caplog.at_level("ERROR"):
        outputs = store.get_for_mission("mission-1")

    assert [output.id for output in outputs] == ["healthy-output"]
    assert malformed.status == "blocked"
    assert malformed.github_message == "Blocked because the persisted project-output snapshot is invalid."
    assert malformed.updated_at >= now
    assert "Quarantining malformed project-output snapshot" in caplog.text
    assert "broken-output" not in caplog.text
    assert sessions[0].commits == 1
