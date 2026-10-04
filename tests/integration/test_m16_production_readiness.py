from company.runtime.dashboard import RuntimeDashboard
from company.runtime.end_to_end import AutonomousExecution
from company.runtime.failure_recovery import RecoveryState, RuntimeFailureRecovery
from company.runtime.observability import RuntimeObservability
from company.runtime.security import RuntimeSecurityGuard


def test_production_runtime_success_path():
    runtime = AutonomousExecution()

    result = runtime.run(
        "production-success",
        lambda: {"status": "ok"},
    )

    assert result.status == "completed"
    assert result.result == {"status": "ok"}
    assert result.error is None


def test_production_runtime_failure_path():
    runtime = AutonomousExecution()

    def failing_operation():
        raise RuntimeError("production failure")

    result = runtime.run(
        "production-failure",
        failing_operation,
    )

    assert result.status == "failed"
    assert result.error == "production failure"
    assert result.attempts == 1


def test_production_runtime_dashboard():
    runtime = AutonomousExecution()

    runtime.run(
        "production-dashboard",
        lambda: "ok",
    )

    snapshot = runtime.dashboard()

    assert snapshot["runs"] == 1
    assert snapshot["completed"] == 1
    assert snapshot["events"] == 2


def test_production_recovery_exhaustion():
    recovery = RuntimeFailureRecovery(max_attempts=2)

    recovery.register("production-recovery")
    recovery.mark_failed("production-recovery", "failure-1")
    recovery.begin_recovery("production-recovery")
    recovery.mark_failed("production-recovery", "failure-2")
    recovery.begin_recovery("production-recovery")
    recovery.exhaust("production-recovery")

    record = recovery.get("production-recovery")

    assert record.state == RecoveryState.EXHAUSTED
    assert not recovery.can_retry("production-recovery")


def test_production_observability():
    observability = RuntimeObservability()

    observability.record(
        "production.started",
        run_id="production-observability",
        status="running",
    )
    observability.record(
        "production.completed",
        run_id="production-observability",
        status="completed",
    )

    assert observability.count() == 2
    assert observability.count("production.completed") == 1


def test_production_dashboard_from_observability():
    observability = RuntimeObservability()

    observability.record(
        "production.started",
        run_id="production-dashboard",
        status="running",
    )
    observability.record(
        "production.completed",
        run_id="production-dashboard",
        status="completed",
    )

    dashboard = RuntimeDashboard(observability).as_dict()

    assert dashboard["runs"] == 1
    assert dashboard["completed"] == 1


def test_production_security_rejects_disallowed_command():
    security = RuntimeSecurityGuard()

    try:
        security.validate_command(["rm", "-rf", "."])
    except Exception:
        return

    raise AssertionError("disallowed command was accepted")
