from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeRecoveryState:
    attempts: int
    max_attempts: int
    recovered: bool
    exhausted: bool


class RuntimeRecoveryController:
    def __init__(self, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        self.max_attempts = max_attempts
        self._attempts = 0
        self._recovered = False
        self._lock = asyncio.Lock()

    async def begin_attempt(self) -> RuntimeRecoveryState:
        async with self._lock:
            self._recovered = False
            self._attempts += 1
            return self._state()

    async def mark_recovered(self) -> RuntimeRecoveryState:
        async with self._lock:
            self._recovered = True
            return self._state()

    async def state(self) -> RuntimeRecoveryState:
        async with self._lock:
            return self._state()

    async def reset(self) -> None:
        async with self._lock:
            self._attempts = 0
            self._recovered = False

    def _state(self) -> RuntimeRecoveryState:
        return RuntimeRecoveryState(
            attempts=self._attempts,
            max_attempts=self.max_attempts,
            recovered=self._recovered,
            exhausted=(
                not self._recovered
                and self._attempts >= self.max_attempts
            ),
        )


class RecoveringProductionRuntime:
    def __init__(
        self,
        runtime,
        recovery: RuntimeRecoveryController,
    ) -> None:
        self.runtime = runtime
        self.recovery = recovery

    async def execute(self, operation) -> object:
        while True:
            state = await self.recovery.begin_attempt()

            try:
                result = await self.runtime.execute(operation)
                await self.recovery.mark_recovered()
                return result
            except Exception:
                if state.exhausted:
                    raise
