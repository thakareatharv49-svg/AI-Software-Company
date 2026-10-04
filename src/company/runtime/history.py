from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True, frozen=True)
class RuntimeExecutionRecord:
    execution_id: str
    started_at: str
    completed_at: str | None
    status: str
    error: str | None


class RuntimeExecutionHistory:
    def __init__(self) -> None:
        self._records: list[RuntimeExecutionRecord] = []
        self._lock = asyncio.Lock()

    async def start(self, execution_id: str) -> RuntimeExecutionRecord:
        record = RuntimeExecutionRecord(
            execution_id=execution_id,
            started_at=datetime.now(UTC).isoformat(),
            completed_at=None,
            status="running",
            error=None,
        )

        async with self._lock:
            self._records.append(record)

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
            return list(self._records)

    async def get(self, execution_id: str) -> RuntimeExecutionRecord | None:
        async with self._lock:
            for record in reversed(self._records):
                if record.execution_id == execution_id:
                    return record
        return None

    async def _update(
        self,
        execution_id: str,
        *,
        status: str,
        error: str | None,
    ) -> RuntimeExecutionRecord:
        async with self._lock:
            for index in range(len(self._records) - 1, -1, -1):
                record = self._records[index]

                if record.execution_id != execution_id:
                    continue

                updated = RuntimeExecutionRecord(
                    execution_id=record.execution_id,
                    started_at=record.started_at,
                    completed_at=datetime.now(UTC).isoformat(),
                    status=status,
                    error=error,
                )

                self._records[index] = updated
                return updated

        raise KeyError(f"unknown execution_id: {execution_id}")


class TrackedProductionRuntime:
    def __init__(
        self,
        runtime,
        history: RuntimeExecutionHistory,
    ) -> None:
        self.runtime = runtime
        self.history = history
        self._counter = 0

    def _next_execution_id(self) -> str:
        self._counter += 1
        return f"runtime-execution-{self._counter}"

    async def execute(self, operation) -> object:
        execution_id = self._next_execution_id()
        await self.history.start(execution_id)

        try:
            result = await self.runtime.execute(operation)
        except Exception as exc:
            await self.history.fail(execution_id, str(exc))
            raise
        else:
            await self.history.complete(execution_id)
            return result
