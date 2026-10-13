from datetime import UTC, datetime
from types import SimpleNamespace

from src.company.persistence import MissionAuditStore


def test_list_for_mission_skips_malformed_audit_rows_without_mutating_them(monkeypatch, caplog):
    import src.company.persistence as persistence

    now = datetime.now(UTC)
    malformed = SimpleNamespace(
        id="broken-audit",
        mission_id="mission-1",
        event_type="created",
        message="safe message",
        status=None,
        timestamp=now,
        metadata=["invalid-shape"],
    )
    healthy = SimpleNamespace(
        id="healthy-audit",
        mission_id="mission-1",
        event_type="progress",
        message="still visible",
        status="running",
        timestamp=now,
        metadata={"stage": "build"},
    )

    class FakeScalars:
        def all(self):
            return [healthy, malformed]

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
    store = MissionAuditStore.__new__(MissionAuditStore)
    store._engine = object()

    with caplog.at_level("ERROR"):
        entries = store.list_for_mission("mission-1")

    assert [entry.id for entry in entries] == ["healthy-audit"]
    assert malformed.metadata == ["invalid-shape"]
    assert "Skipping malformed mission-audit snapshot" in caplog.text
    assert "broken-audit" not in caplog.text
    assert "invalid-shape" not in caplog.text
