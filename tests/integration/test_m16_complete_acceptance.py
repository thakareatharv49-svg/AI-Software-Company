from company.runtime.dashboard import RuntimeDashboard
from company.runtime.end_to_end import AutonomousExecution
from company.runtime.failure_recovery import RecoveryState, RuntimeFailureRecovery
from company.runtime.observability import RuntimeObservability
from company.runtime.security import RuntimeSecurityGuard


def test_m16_complete_autonomous_success():
    runtime = AutonomousExecution()

    result = runtime.run(
        "m16-complete-success",
        lambda: {"status": "completed"},
    )

    assert result.status == "completed"
    assert result.result == {"status": "completed"}
    assert result.error is None


def test_m16_complete_autonomous_failure():
    runtime = AutonomousExecution()

    def failing_operation():
        raise RuntimeError("m16 failure")

    result = runtime.run(
        "m16-complete-failure",
        failing_operation,
    )

    assert result.status == "failed"
    assert result.error == "m16 failure"
    assert result.attempts == 1


def test_m16_complete_recovery_exhaustion():
    recovery = RuntimeFailureRecovery(max_attempts=1)

    recovery.register("m16-complete-recovery")
    recovery.mark_failed("m16-complete-recovery", "failure")
    recovery.begin_recovery("m16-complete-recovery")
    recovery.exhaust("m16-complete-recovery")

    record = recovery.get("m16-complete-recovery")

    assert record.state == RecoveryState.EXHAUSTED
    assert not recovery.can_retry("m16-complete-recovery")


def test_m16_complete_security_boundary():
    security = RuntimeSecurityGuard()

    try:
        security.validate_command(["rm", "-rf", "/"])
    except Exception:
        pass
    else:
        raise AssertionError("unsafe command was accepted")


def test_m16_complete_observability():
    observability = RuntimeObservability()

    observability.record(
        "m16.started",
        run_id="m16-complete-observability",
        status="running",
    )
    observability.record(
        "m16.completed",
        run_id="m16-complete-observability",
        status="completed",
    )

    assert observability.count() == 2
    assert observability.count("m16.completed") == 1


def test_m16_complete_dashboard():
    observability = RuntimeObservability()

    observability.record(
        "m16.started",
        run_id="m16-complete-dashboard",
        status="running",
    )
    observability.record(
        "m16.completed",
        run_id="m16-complete-dashboard",
        status="completed",
    )

    dashboard = RuntimeDashboard(observability).as_dict()

    assert dashboard["runs"] == 1
    assert dashboard["events"] == 2
    assert dashboard["completed"] == 1


def test_m16_complete_runtime_dashboard():
    runtime = AutonomousExecution()

    runtime.run(
        "m16-complete-runtime-dashboard",
        lambda: "ok",
    )

    dashboard = runtime.dashboard()

    assert dashboard["runs"] == 1
    assert dashboard["events"] == 2
    assert dashboard["completed"] == 1
