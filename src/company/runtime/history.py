from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True, frozen=True)
class RuntimeExecutionRecord:
    execution_id: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    error: str | None = None


class RuntimeExecutionHistory:
    def __init__(self) -> None:
        self._records: dict[str, RuntimeExecutionRecord] = {}
        self._lock = asyncio.Lock()

    async def start(self, execution_id: str) -> RuntimeExecutionRecord:
        async with self._lock:
            record = RuntimeExecutionRecord(
                execution_id=execution_id,
                started_at=datetime.now(UTC),
                completed_at=None,
                status="running",
            )
            self._records[execution_id] = record
            return record

    async def complete(self, execution_id: str) -> RuntimeExecutionRecord:
        return await self._update(
            execution_id,
            status="completed",
            error=None,
        )

    async def fail(
        self,
        execution_id: str,
        error: str,
    ) -> RuntimeExecutionRecord:
        return await self._update(
            execution_id,
            status="failed",
            error=error,
        )

    async def records(self) -> list[RuntimeExecutionRecord]:
        async with self._lock:
            return list(self._records.values())

    async def get(self, execution_id: str) -> RuntimeExecutionRecord | None:
        async with self._lock:
            return self._records.get(execution_id)

    async def _update(
        self,
        execution_id: str,
        *,
        status: str,
        error: str | None,
    ) -> RuntimeExecutionRecord:
        async with self._lock:
            record = self._records.get(execution_id)

            if record is None:
                raise KeyError(f"Unknown execution: {execution_id}")

            updated = RuntimeExecutionRecord(
                execution_id=record.execution_id,
                started_at=record.started_at,
                completed_at=datetime.now(UTC),
                status=status,
                error=error,
            )

            self._records[execution_id] = updated
            return updated


class TrackedProductionRuntime:
    def __init__(
        self,
        runtime,
        history: RuntimeExecutionHistory,
    ) -> None:
        self.runtime = runtime
        self.history = history
        self._counter = 0

    async def execute(self, operation):
        self._counter += 1
        execution_id = f"runtime-execution-{self._counter}"

        await self.history.start(execution_id)

        try:
            result = await self.runtime.execute(operation)
        except Exception as exc:
            await self.history.fail(execution_id, str(exc))
            raise
        else:
            await self.history.complete(execution_id)
            return result
