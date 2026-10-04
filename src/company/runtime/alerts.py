from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeAlert:
    level: str
    message: str
    metric: str
    value: int
    threshold: int


class RuntimeAlertManager:
    def __init__(self) -> None:
        self._alerts: list[RuntimeAlert] = []
        self._lock = asyncio.Lock()

    async def check(
        self,
        *,
        metric: str,
        value: int,
        threshold: int,
        message: str,
        level: str = "warning",
    ) -> RuntimeAlert | None:
        if threshold < 0:
            raise ValueError("threshold must be >= 0")

        if value <= threshold:
            return None

        alert = RuntimeAlert(
            level=level,
            message=message,
            metric=metric,
            value=value,
            threshold=threshold,
        )

        async with self._lock:
            self._alerts.append(alert)

        return alert

    async def alerts(self) -> list[RuntimeAlert]:
        async with self._lock:
            return list(self._alerts)

    async def clear(self) -> None:
        async with self._lock:
            self._alerts.clear()


class RuntimeAlertingExecutor:
    def __init__(
        self,
        operation: Callable[[], Awaitable[object]],
        alerts: RuntimeAlertManager,
    ) -> None:
        self.operation = operation
        self.alerts = alerts

    async def execute(self) -> object:
        try:
            return await self.operation()
        except Exception as exc:
            await self.alerts.check(
                metric="execution_failures",
                value=1,
                threshold=0,
                message=str(exc),
                level="error",
            )
            raise
