from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeRateLimitState:
    allowed: bool
    current: int
    limit: int
    rejected: int


class RuntimeRateLimiter:
    def __init__(self, limit: int = 10) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        self.limit = limit
        self._current = 0
        self._rejected = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            if self._current >= self.limit:
                self._rejected += 1
                return False

            self._current += 1
            return True

    async def release(self) -> None:
        async with self._lock:
            if self._current > 0:
                self._current -= 1

    async def state(self) -> RuntimeRateLimitState:
        async with self._lock:
            return RuntimeRateLimitState(
                allowed=self._current < self.limit,
                current=self._current,
                limit=self.limit,
                rejected=self._rejected,
            )

    async def reset(self) -> None:
        async with self._lock:
            self._current = 0
            self._rejected = 0


class RuntimeRateLimitError(RuntimeError):
    pass


class RateLimitedRuntime:
    def __init__(self, runtime, limiter: RuntimeRateLimiter) -> None:
        self.runtime = runtime
        self.limiter = limiter

    async def execute(self, operation):
        allowed = await self.limiter.acquire()

        if not allowed:
            raise RuntimeRateLimitError("runtime rate limit exceeded")

        try:
            return await self.runtime.execute(operation)
        finally:
            await self.limiter.release()
