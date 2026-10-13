from datetime import UTC, datetime

from src.company.events.events import CompanyEvent


def test_company_event_redacts_sensitive_text_before_exposure():
    timestamp = datetime(2026, 10, 13, tzinfo=UTC)
    event = CompanyEvent(
        event_type="MISSION_DIAGNOSTIC",
        message=(
            "Worker failed with api_key=eventSecret123456 and "
            "Authorization: Bearer verySensitiveCredentialValue123"
        ),
        project_id="project:token=projectSecret123456",
        task_id="task-password=taskSecret123456",
        timestamp=timestamp,
    )

    serialized = repr(event)
    for secret in (
        "eventSecret123456",
        "verySensitiveCredentialValue123",
        "projectSecret123456",
        "taskSecret123456",
    ):
        assert secret not in serialized
    assert "api_key=[REDACTED]" in event.message
    assert "[REDACTED]" in event.message
    assert event.project_id == "project:token=[REDACTED_TOKEN]"
    assert event.task_id == "task-password=[REDACTED]"
    assert event.timestamp == timestamp


def test_company_event_bounds_untrusted_message_length():
    event = CompanyEvent(
        event_type="MISSION_DIAGNOSTIC",
        message="diagnostic " * 1000,
    )

    assert len(event.message) == 4000
