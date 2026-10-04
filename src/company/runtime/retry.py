from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeRetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.0
    max_delay_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be >= 0")
        if self.max_delay_seconds < 0:
            raise ValueError("max_delay_seconds must be >= 0")
        if self.base_delay_seconds > self.max_delay_seconds:
            raise ValueError(
                "base_delay_seconds must be <= max_delay_seconds"
            )

    def delay_for(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")

        delay = self.base_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


@dataclass(slots=True, frozen=True)
class RuntimeRetryResult:
    attempts: int
    succeeded: bool


class RuntimeRetryController:
    def __init__(self, policy: RuntimeRetryPolicy | None = None) -> None:
        self.policy = policy or RuntimeRetryPolicy()

    async def execute(self, operation) -> RuntimeRetryResult:
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                await operation()
                return RuntimeRetryResult(
                    attempts=attempt,
                    succeeded=True,
                )
            except Exception:
                if attempt >= self.policy.max_attempts:
                    raise

                delay = self.policy.delay_for(attempt)

                if delay > 0:
                    await asyncio.sleep(delay)

        raise RuntimeError("Retry execution ended unexpectedly")
