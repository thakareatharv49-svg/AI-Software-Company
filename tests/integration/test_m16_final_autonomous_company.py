from company.runtime.dashboard import RuntimeDashboard
from company.runtime.end_to_end import AutonomousExecution
from company.runtime.failure_recovery import RecoveryState, RuntimeFailureRecovery
from company.runtime.observability import RuntimeObservability
from company.runtime.security import RuntimeSecurityGuard


def test_m16_final_success_execution():
    runtime = AutonomousExecution()

    result = runtime.run(
        "m16-final-success",
        lambda: {"message": "autonomous execution complete"},
    )

    assert result.status == "completed"
    assert result.result == {"message": "autonomous execution complete"}
    assert result.error is None


def test_m16_final_failure_recovery():
    recovery = RuntimeFailureRecovery(max_attempts=2)

    recovery.register("m16-final-recovery")
    recovery.mark_failed("m16-final-recovery", "failure")
    recovery.begin_recovery("m16-final-recovery")
    recovery.exhaust("m16-final-recovery")

    record = recovery.get("m16-final-recovery")

    assert record.state == RecoveryState.EXHAUSTED
    assert not recovery.can_retry("m16-final-recovery")


def test_m16_final_security_boundary():
    security = RuntimeSecurityGuard()

    try:
        security.validate_command(["rm", "-rf", "."])
    except Exception:
        pass
    else:
        raise AssertionError("unsafe command was accepted")


def test_m16_final_observability_and_dashboard():
    observability = RuntimeObservability()

    observability.record(
        "autonomous_run.started",
        run_id="m16-final-dashboard",
        status="running",
    )
    observability.record(
        "autonomous_run.completed",
        run_id="m16-final-dashboard",
        status="completed",
    )

    dashboard = RuntimeDashboard(observability).as_dict()

    assert dashboard["runs"] == 1
    assert dashboard["events"] == 2
    assert dashboard["completed"] == 1


def test_m16_final_runtime_dashboard():
    runtime = AutonomousExecution()

    runtime.run(
        "m16-final-runtime-dashboard",
        lambda: "ok",
    )

    dashboard = runtime.dashboard()

    assert dashboard["runs"] == 1
    assert dashboard["events"] == 2
    assert dashboard["completed"] == 1
