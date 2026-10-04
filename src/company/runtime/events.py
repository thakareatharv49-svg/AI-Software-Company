from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True, frozen=True)
class RuntimeEvent:
    event_type: str
    timestamp: str
    payload: dict[str, object]


class RuntimeEventRecorder:
    def __init__(self) -> None:
        self._events: list[RuntimeEvent] = []
        self._lock = asyncio.Lock()

    async def record(
        self,
        event_type: str,
        payload: dict[str, object] | None = None,
    ) -> RuntimeEvent:
        event = RuntimeEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC).isoformat(),
            payload=dict(payload or {}),
        )

        async with self._lock:
            self._events.append(event)

        return event

    async def list_events(self) -> list[RuntimeEvent]:
        async with self._lock:
            return list(self._events)

    async def events_by_type(self, event_type: str) -> list[RuntimeEvent]:
        async with self._lock:
            return [
                event
                for event in self._events
                if event.event_type == event_type
            ]

    async def clear(self) -> None:
        async with self._lock:
            self._events.clear()


class ObservableProductionRuntime:
    def __init__(self, runtime, recorder: RuntimeEventRecorder) -> None:
        self.runtime = runtime
        self.recorder = recorder

    async def start(self) -> None:
        await self.runtime.start()
        await self.recorder.record("runtime.started")

    async def stop(self) -> None:
        await self.runtime.stop()
        await self.recorder.record("runtime.stopped")

    async def execute(self, operation) -> object:
        await self.recorder.record("runtime.execution.started")

        try:
            result = await self.runtime.execute(operation)

            await self.recorder.record(
                "runtime.execution.completed",
                {"timed_out": getattr(result, "timed_out", False)},
            )

            return result

        except Exception as exc:
            await self.recorder.record(
                "runtime.execution.failed",
                {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            raise
