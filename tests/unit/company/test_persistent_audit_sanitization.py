from datetime import UTC, datetime

from src.company.audit import MissionAuditEntry
from src.company.persistence import _safe_audit_entry


def test_audit_entries_redact_and_bound_message_and_metadata() -> None:
    entry = MissionAuditEntry(
        id="audit-1",
        mission_id="mission-1",
        event_type="mission.completed",
        message="token=" + "samplevalue123456 " + ("m" * 5000),
        status="completed",
        timestamp=datetime.now(UTC),
        metadata={
            "api_key": "sample-key-value",
            "nested": {"note": "password=" + "sample-value", "large": "x" * 4000},
            "many": list(range(150)),
        },
    )

    safe = _safe_audit_entry(entry)

    assert "samplevalue123456" not in safe.message
    assert len(safe.message) == 4000
    assert safe.metadata["api_key"] == "[REDACTED]"
    assert "sample-value" not in safe.metadata["nested"]["note"]
    assert len(safe.metadata["nested"]["large"]) == 2000
    assert len(safe.metadata["many"]) == 100
    assert safe.timestamp == entry.timestamp


def test_audit_entry_bounds_depth_and_identifier_text() -> None:
    entry = MissionAuditEntry(
        id="i" * 200,
        mission_id="mission-2",
        event_type="e" * 200,
        message="ordinary audit event",
        metadata={"a": {"b": {"c": {"d": {"e": {"f": "too deep"}}}}}},
    )

    safe = _safe_audit_entry(entry)

    assert len(safe.id) == 100
    assert len(safe.event_type) == 100
    assert safe.metadata["a"]["b"]["c"]["d"]["e"]["f"] == "[TRUNCATED]"
