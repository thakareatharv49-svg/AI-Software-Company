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
