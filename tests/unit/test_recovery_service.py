from src.company.recovery.service import RecoveryService


def test_recovery_retries_until_limit() -> None:
    service = RecoveryService(max_attempts=3)

    first = service.record_failure(RuntimeError("boom"), "project-1")
    second = service.record_failure(RuntimeError("boom"), "project-1")
    third = service.record_failure(RuntimeError("boom"), "project-1")

    assert first.action == "retry"
    assert first.retryable is True
    assert first.attempt == 1

    assert second.action == "retry"
    assert second.retryable is True
    assert second.attempt == 2

    assert third.action == "block"
    assert third.retryable is False
    assert third.attempt == 3


def test_recovery_attempts_are_isolated_per_project() -> None:
    service = RecoveryService(max_attempts=2)

    service.record_failure(RuntimeError("a"), "project-a")
    result = service.record_failure(RuntimeError("b"), "project-b")

    assert result.attempt == 1
    assert service.attempts("project-a") == 1
    assert service.attempts("project-b") == 1


def test_recovery_reset() -> None:
    service = RecoveryService(max_attempts=2)

    service.record_failure(RuntimeError("boom"), "project-1")
    service.reset("project-1")

    assert service.attempts("project-1") == 0


def test_invalid_max_attempts() -> None:
    try:
        RecoveryService(max_attempts=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")
