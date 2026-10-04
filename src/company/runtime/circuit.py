from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeCircuitState:
    failures: int
    threshold: int
    open: bool


class RuntimeCircuitBreaker:
    def __init__(self, failure_threshold: int = 3) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")

        self.failure_threshold = failure_threshold
        self._failures = 0
        self._open = False
        self._lock = asyncio.Lock()

    async def allow(self) -> bool:
        async with self._lock:
            return not self._open

    async def record_success(self) -> RuntimeCircuitState:
        async with self._lock:
            self._failures = 0
            self._open = False
            return self._state()

    async def record_failure(self) -> RuntimeCircuitState:
        async with self._lock:
            self._failures += 1

            if self._failures >= self.failure_threshold:
                self._open = True

            return self._state()

    async def reset(self) -> RuntimeCircuitState:
        async with self._lock:
            self._failures = 0
            self._open = False
            return self._state()

    async def state(self) -> RuntimeCircuitState:
        async with self._lock:
            return self._state()

    def _state(self) -> RuntimeCircuitState:
        return RuntimeCircuitState(
            failures=self._failures,
            threshold=self.failure_threshold,
            open=self._open,
        )


class CircuitOpenError(RuntimeError):
    pass


class CircuitProtectedRuntime:
    def __init__(
        self,
        runtime,
        circuit: RuntimeCircuitBreaker,
    ) -> None:
        self.runtime = runtime
        self.circuit = circuit

    async def execute(self, operation):
        if not await self.circuit.allow():
            raise CircuitOpenError("runtime circuit is open")

        try:
            result = await self.runtime.execute(operation)
        except Exception:
            await self.circuit.record_failure()
            raise
        else:
            await self.circuit.record_success()
            return result
