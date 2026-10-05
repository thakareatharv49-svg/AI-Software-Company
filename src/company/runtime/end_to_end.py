from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from company.memory import MemoryIntegration, MemoryStore

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
    context: dict[str, object] | None = None


class AutonomousExecution:
    def __init__(
        self,
        *,
        observability: RuntimeObservability | None = None,
        recovery: RuntimeFailureRecovery | None = None,
        security: RuntimeSecurityGuard | None = None,
        memory: MemoryIntegration | None = None,
        memory_store: MemoryStore | None = None,
    ) -> None:
        self.observability = observability or RuntimeObservability()
        self.recovery = recovery or RuntimeFailureRecovery()
        self.security = security or RuntimeSecurityGuard()

        if memory is not None and memory_store is not None:
            raise ValueError("provide either memory or memory_store, not both")

        self.memory = memory or MemoryIntegration.create(memory_store)

    def build_context(
        self,
        *,
        query: str,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, object]:
        return self.memory.context(
            query=query,
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
        )

    def run(
        self,
        run_id: str,
        operation: Callable[[], Any],
        *,
        project_id: str | None = None,
        agent_id: str | None = None,
        context_query: str | None = None,
    ) -> AutonomousExecutionResult:
        self.recovery.register(run_id)

        query = context_query or f"autonomous execution {run_id}"

        context = self.build_context(
            query=query,
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
        )

        self.memory.record_execution_started(
            run_id=run_id,
            project_id=project_id,
            agent_id=agent_id,
            query=query,
        )

        self.observability.record(
            "autonomous_run.started",
            run_id=run_id,
            status="running",
        )

        try:
            self.security.validate_command(["python", "--version"])
        except Exception as exc:
            self.recovery.mark_failed(run_id, str(exc))
            self.memory.record_execution_failed(
                run_id=run_id,
                error=str(exc),
                project_id=project_id,
                agent_id=agent_id,
            )
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
                context=context,
            )

        attempts = 1

        try:
            result = operation()

            self.recovery.mark_recovered(
                run_id,
                {"strategy": "direct_execution", "attempts": attempts},
            )

            self.memory.record_execution_completed(
                run_id=run_id,
                result=result,
                project_id=project_id,
                agent_id=agent_id,
            )

            self.observability.record(
                "autonomous_run.completed",
                run_id=run_id,
                status="completed",
                metadata={"attempts": attempts},
            )

            return AutonomousExecutionResult(
                run_id=run_id,
                status="completed",
                attempts=attempts,
                result=result,
                context=context,
            )

        except Exception as exc:
            self.recovery.mark_failed(run_id, str(exc))

            self.memory.record_execution_failed(
                run_id=run_id,
                error=str(exc),
                project_id=project_id,
                agent_id=agent_id,
            )

            self.observability.record(
                "autonomous_run.failed",
                run_id=run_id,
                status="failed",
                metadata={"stage": "execution", "attempts": attempts},
            )

            return AutonomousExecutionResult(
                run_id=run_id,
                status="failed",
                attempts=attempts,
                error=str(exc),
                context=context,
            )
    def run_with_timeout(
        self,
        run_id: str,
        operation: Callable[[], Any],
        timeout_seconds: float,
        *,
        project_id: str | None = None,
        agent_id: str | None = None,
        context_query: str | None = None,
    ) -> AutonomousExecutionResult:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self.run,
            run_id,
            operation,
            project_id=project_id,
            agent_id=agent_id,
            context_query=context_query,
        )

        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError:
            error = (
                f"execution timed out after "
                f"{timeout_seconds} seconds"
            )

            self.recovery.mark_failed(run_id, error)
            self.memory.record_execution_failed(
                run_id=run_id,
                error=error,
                project_id=project_id,
                agent_id=agent_id,
            )

            self.observability.record(
                "autonomous_run.timeout",
                run_id=run_id,
                status="failed",
                metadata={"timeout_seconds": timeout_seconds},
            )

            return AutonomousExecutionResult(
                run_id=run_id,
                status="failed",
                attempts=max(
                    1,
                    self.recovery.get(run_id).attempts,
                ),
                error=error,
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def dashboard(self) -> dict[str, Any]:
        return RuntimeDashboard(self.observability).as_dict()
