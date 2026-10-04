
import pytest

from company.runtime.failure_recovery import (
    RecoveryState,
    RuntimeFailureRecovery,
)


def test_registers_run():
    recovery = RuntimeFailureRecovery()

    record = recovery.register("run-1")

    assert record.run_id == "run-1"
    assert record.state == RecoveryState.HEALTHY
    assert record.attempts == 0


def test_unknown_run():
    recovery = RuntimeFailureRecovery()

    with pytest.raises(KeyError):
        recovery.get("missing")


def test_failure_and_recovery():
    recovery = RuntimeFailureRecovery(max_attempts=3)
    recovery.register("run-1")

    failed = recovery.mark_failed(
        "run-1",
        "pipeline failed",
        {"stage": "engineering"},
    )

    assert failed.state == RecoveryState.FAILED
    assert failed.last_error == "pipeline failed"
    assert failed.metadata["stage"] == "engineering"

    recovering = recovery.begin_recovery("run-1")

    assert recovering.state == RecoveryState.RECOVERING
    assert recovering.attempts == 1

    recovered = recovery.mark_recovered(
        "run-1",
        {"strategy": "retry"},
    )

    assert recovered.state == RecoveryState.RECOVERED
    assert recovered.last_error is None
    assert recovered.metadata["strategy"] == "retry"


def test_retry_limit():
    recovery = RuntimeFailureRecovery(max_attempts=2)
    recovery.register("run-1")

    recovery.mark_failed("run-1", "error")
    recovery.begin_recovery("run-1")
    recovery.mark_failed("run-1", "error")
    recovery.begin_recovery("run-1")

    assert recovery.get("run-1").attempts == 2
    assert recovery.get("run-1").state == RecoveryState.RECOVERING
    assert not recovery.can_retry("run-1")

    exhausted = recovery.begin_recovery("run-1")

    assert exhausted.state == RecoveryState.EXHAUSTED
    assert exhausted.attempts == 2


def test_explicit_exhaustion():
    recovery = RuntimeFailureRecovery()
    recovery.register("run-1")

    record = recovery.exhaust("run-1")

    assert record.state == RecoveryState.EXHAUSTED
    assert not recovery.can_retry("run-1")


def test_records_returns_all_runs():
    recovery = RuntimeFailureRecovery()

    recovery.register("run-1")
    recovery.register("run-2")

    records = recovery.records()

    assert len(records) == 2
    assert {record.run_id for record in records} == {
        "run-1",
        "run-2",
    }


def test_invalid_max_attempts():
    with pytest.raises(ValueError):
        RuntimeFailureRecovery(max_attempts=0)
