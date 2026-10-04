
from company.runtime.dashboard import RuntimeDashboard
from company.runtime.failure_recovery import (
    RecoveryState,
    RuntimeFailureRecovery,
)
from company.runtime.observability import RuntimeObservability
from company.runtime.security import (
    RuntimeSecurityError,
    RuntimeSecurityGuard,
)


def test_m16_autonomous_company_runtime_acceptance(tmp_path):
    observability = RuntimeObservability(
        tmp_path / "runtime-events.jsonl"
    )
    recovery = RuntimeFailureRecovery(max_attempts=2)
    security = RuntimeSecurityGuard()

    run_id = "acceptance-run"

    recovery.register(run_id)

    observability.record(
        "run.started",
        run_id=run_id,
        status="running",
        metadata={"phase": "acceptance"},
    )

    security.validate_command(["python", "--version"])

    try:
        security.validate_command(
            ["powershell", "-Command", "whoami"]
        )
        raise AssertionError("unsafe command was accepted")
    except RuntimeSecurityError:
        pass

    recovery.mark_failed(
        run_id,
        "simulated transient failure",
        {"phase": "execution"},
    )

    recovery.begin_recovery(run_id)

    assert recovery.can_retry(run_id)

    recovery.mark_recovered(
        run_id,
        {"strategy": "retry"},
    )

    assert recovery.get(run_id).state == RecoveryState.RECOVERED

    observability.record(
        "run.completed",
        run_id=run_id,
        status="completed",
        duration_seconds=0.01,
    )

    dashboard = RuntimeDashboard(observability)
    snapshot = dashboard.snapshot("healthy")

    assert snapshot.status == "healthy"
    assert snapshot.runs == 1
    assert snapshot.completed == 1
    assert snapshot.failed == 0
    assert snapshot.events == 2

    assert (tmp_path / "runtime-events.jsonl").exists()


def test_m16_recovery_exhaustion_acceptance():
    recovery = RuntimeFailureRecovery(max_attempts=2)
    run_id = "exhaustion-run"

    recovery.register(run_id)

    recovery.mark_failed(run_id, "failure-1")
    recovery.begin_recovery(run_id)

    recovery.mark_failed(run_id, "failure-2")
    recovery.begin_recovery(run_id)

    assert recovery.get(run_id).attempts == 2
    assert not recovery.can_retry(run_id)

    exhausted = recovery.begin_recovery(run_id)

    assert exhausted.state == RecoveryState.EXHAUSTED
    assert not recovery.can_retry(run_id)


def test_m16_security_environment_acceptance():
    security = RuntimeSecurityGuard()

    environment = {
        "PATH": "safe",
        "APP_ENV": "production",
        "GITHUB_TOKEN": "must-not-leak",
        "GH_TOKEN": "must-not-leak",
    }

    sanitized = security.sanitize_environment(environment)

    assert "GITHUB_TOKEN" not in sanitized
    assert "GH_TOKEN" not in sanitized
    assert sanitized["APP_ENV"] == "production"
    assert sanitized["PATH"] == "safe"
