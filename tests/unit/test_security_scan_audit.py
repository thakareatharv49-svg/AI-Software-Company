from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.company.review_routes import _assert_artifact_security


def test_blocked_security_scan_emits_metadata_only_audit_event() -> None:
    events = []
    center = SimpleNamespace(
        _audit=lambda *args, **kwargs: events.append((args, kwargs))
    )
    private_value = "not-for-audit-log-credential"

    with pytest.raises(HTTPException):
        _assert_artifact_security(
            "audit-test",
            {"settings.py": f'api_key = "{private_value}"'},
            center,
        )

    assert len(events) == 1
    args, kwargs = events[0]
    assert args[1] == "SECURITY_SCAN_BLOCKED"
    assert kwargs["status"] == "blocked"
    assert kwargs["metadata"]["finding_count"] >= 1
    assert private_value not in repr(events)


def test_mission_audit_entry_redacts_sensitive_message_and_metadata() -> None:
    from src.company.audit import MissionAuditEntry

    token = "ghp_" + "Z" * 32
    entry = MissionAuditEntry(
        id="audit-redaction",
        mission_id="mission-a",
        event_type="tool_failure",
        message="Provider error with token " + token,
        metadata={
            "api_key": token,
            "details": {"password": "plain-text-password", "status": "failed"},
        },
    )

    serialized = entry.model_dump_json()
    assert token not in serialized
    assert "plain-text-password" not in serialized
    assert entry.metadata["api_key"] == "[REDACTED]"
    assert entry.metadata["details"]["password"] == "[REDACTED]"
    assert entry.metadata["details"]["status"] == "failed"
