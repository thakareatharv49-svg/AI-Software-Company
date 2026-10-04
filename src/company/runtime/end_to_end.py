
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .dashboard import RuntimeDashboard
from .failure_recovery import RuntimeFailureRecovery
from .observability import RuntimeObservability
from .security import RuntimeSecurityGuard


@dataclass
class AutonomousExecutionResult:
    run_id: str
    status: str
    attempts: int
    result: Any = None
    error: str | None = None


class AutonomousExecution:
    def __init__(
        self,
        *,
        observability: RuntimeObservability | None = None,
        recovery: RuntimeFailureRecovery | None = None,
        security: RuntimeSecurityGuard | None = None,
    ) -> None:
        self.observability = observability or RuntimeObservability()
        self.recovery = recovery or RuntimeFailureRecovery()
        self.security = security or RuntimeSecurityGuard()

    def run(
        self,
        run_id: str,
        operation: Callable[[], Any],
    ) -> AutonomousExecutionResult:
        self.recovery.register(run_id)

        self.observability.record(
            "autonomous_run.started",
            run_id=run_id,
            status="running",
        )

        try:
            self.security.validate_command(["python", "--version"])
        except Exception as exc:
            self.recovery.mark_failed(run_id, str(exc))
            self.observability.record(
                "autonomous_run.failed",
                run_id=run_id,
                status="failed",
                metadata={"stage": "security"},
            )
            return AutonomousExecutionResult(
                run_id=run_id,
                status="failed",
                attempts=0,
                error=str(exc),
            )

        try:
            result = operation()

            self.recovery.mark_recovered(
                run_id,
                {"strategy": "direct_execution"},
            )

            self.observability.record(
                "autonomous_run.completed",
                run_id=run_id,
                status="completed",
            )

            return AutonomousExecutionResult(
                run_id=run_id,
                status="completed",
                attempts=self.recovery.get(run_id).attempts,
                result=result,
            )

        except Exception as exc:
            self.recovery.mark_failed(run_id, str(exc))

            if self.recovery.can_retry(run_id):
                self.recovery.begin_recovery(run_id)

            self.observability.record(
                "autonomous_run.failed",
                run_id=run_id,
                status="failed",
                metadata={"stage": "execution"},
            )

            return AutonomousExecutionResult(
                run_id=run_id,
                status="failed",
                attempts=self.recovery.get(run_id).attempts,
                error=str(exc),
            )

    def dashboard(self) -> dict[str, Any]:
        return RuntimeDashboard(self.observability).as_dict()
