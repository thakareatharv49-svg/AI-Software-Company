from company.runtime.end_to_end import AutonomousExecution
from company.runtime.failure_recovery import RecoveryState, RuntimeFailureRecovery
from company.runtime.observability import RuntimeObservability
from company.runtime.security import RuntimeSecurityGuard


def test_release_ready_autonomous_success():
    runtime = AutonomousExecution()

    result = runtime.run(
        "release-success",
        lambda: {"release": "ready"},
    )

    assert result.status == "completed"
    assert result.result == {"release": "ready"}


def test_release_ready_autonomous_failure():
    runtime = AutonomousExecution()

    def failing_operation():
        raise RuntimeError("release failure")

    result = runtime.run("release-failure", failing_operation)

    assert result.status == "failed"
    assert result.error == "release failure"
    assert result.attempts == 1


def test_release_ready_recovery_exhaustion():
    recovery = RuntimeFailureRecovery(max_attempts=1)

    recovery.register("release-recovery")
    recovery.mark_failed("release-recovery", "failure")
    recovery.begin_recovery("release-recovery")
    recovery.exhaust("release-recovery")

    record = recovery.get("release-recovery")

    assert record.state == RecoveryState.EXHAUSTED
    assert not recovery.can_retry("release-recovery")


def test_release_ready_security_boundary():
    security = RuntimeSecurityGuard()

    try:
        security.validate_command(["rm", "-rf", "/"])
    except Exception:
        pass
    else:
        raise AssertionError("unsafe command accepted")


def test_release_ready_observability():
    observability = RuntimeObservability()

    observability.record(
        "release.started",
        run_id="release-observability",
        status="running",
    )
    observability.record(
        "release.completed",
        run_id="release-observability",
        status="completed",
    )

    assert observability.count() == 2
    assert observability.count("release.completed") == 1
