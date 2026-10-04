from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from company.runtime.execution_result import (
    AutonomousExecutionResult,
    AutonomousExecutionStatus,
)


class AutonomousExecutor:
    """Runs the real company pipeline and exposes deterministic lifecycle state."""

    def __init__(
        self,
        pipeline: Callable[[Any], Awaitable[Any]],
    ) -> None:
        if not callable(pipeline):
            raise TypeError("pipeline must be callable")

        self._pipeline = pipeline
        self._tasks: dict[str, asyncio.Task[AutonomousExecutionResult]] = {}

    async def execute(
        self,
        run_id: str,
        mission: Any,
    ) -> AutonomousExecutionResult:
        if not run_id:
            raise ValueError("run_id must not be empty")

        if run_id in self._tasks:
            raise ValueError(f"run already exists: {run_id}")

        task = asyncio.create_task(
            self._execute(run_id, mission)
        )
        self._tasks[run_id] = task

        return AutonomousExecutionResult(
            run_id=run_id,
            status=AutonomousExecutionStatus.ACCEPTED,
        )

    async def _execute(
        self,
        run_id: str,
        mission: Any,
    ) -> AutonomousExecutionResult:
        try:
            result = await self._pipeline(mission)

            return AutonomousExecutionResult(
                run_id=run_id,
                status=AutonomousExecutionStatus.COMPLETED,
                result=result,
            )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            return AutonomousExecutionResult(
                run_id=run_id,
                status=AutonomousExecutionStatus.FAILED,
                error=str(exc),
            )

    async def wait(
        self,
        run_id: str,
    ) -> AutonomousExecutionResult:
        task = self._tasks.get(run_id)

        if task is None:
            raise KeyError(run_id)

        return await task

    def running(self, run_id: str) -> bool:
        task = self._tasks.get(run_id)

        return task is not None and not task.done()

    def forget(self, run_id: str) -> None:
        self._tasks.pop(run_id, None)
