import pytest

from src.company.mission_controller.failure_policy import (
    MAX_REPAIR_ATTEMPTS,
    FailureKind,
    bounded_repair_attempts,
    classify_failure,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("AssertionError: expected 200 but got 500", FailureKind.REPAIRABLE),
        ("QA test failed: test_login_requires_valid_session", FailureKind.REPAIRABLE),
        ("Connection timed out while calling the model provider", FailureKind.TRANSIENT),
        ("HTTP 503 service unavailable", FailureKind.TRANSIENT),
        ("GitHub secondary rate limit; try again later", FailureKind.NON_RETRYABLE),
        ("Unauthorized: invalid API key", FailureKind.NON_RETRYABLE),
        ("Permission denied while creating repository", FailureKind.NON_RETRYABLE),
        ("", FailureKind.REPAIRABLE),
    ],
)
def test_classify_failure(message: str, expected: FailureKind) -> None:
    assert classify_failure(message) == expected


def test_non_retryable_markers_take_precedence_over_transient_markers() -> None:
    assert classify_failure("timeout: GitHub secondary rate limit") == FailureKind.NON_RETRYABLE


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (1, 1),
        (MAX_REPAIR_ATTEMPTS, MAX_REPAIR_ATTEMPTS),
        (MAX_REPAIR_ATTEMPTS + 100, MAX_REPAIR_ATTEMPTS),
        (-10, 0),
        (True, 0),
        (None, MAX_REPAIR_ATTEMPTS),
        ("not-a-number", MAX_REPAIR_ATTEMPTS),
    ],
)
def test_repair_attempts_are_bounded(value: object, expected: int) -> None:
    assert bounded_repair_attempts(value) == expected
