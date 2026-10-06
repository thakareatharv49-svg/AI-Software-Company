from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass(frozen=True, slots=True)
class ProjectRunResult:
    project_id: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: int = 0


class ConcurrentProjectRunner:
    """Runs independent projects concurrently with a configurable capacity."""

    def __init__(self, max_concurrency: int = 2) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        self.max_concurrency = max_concurrency

    async def run(
        self,
        projects: list[tuple[str, Callable[[], Awaitable[Any]]]],
    ) -> list[ProjectRunResult]:
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def execute(
            project_id: str,
            operation: Callable[[], Awaitable[Any]],
        ) -> ProjectRunResult:
            started = perf_counter()
            async with semaphore:
                try:
                    output = await operation()
                    return ProjectRunResult(
                        project_id,
                        True,
                        output,
                        duration_ms=int((perf_counter() - started) * 1000),
                    )
                except Exception as exc:
                    return ProjectRunResult(
                        project_id,
                        False,
                        error=str(exc),
                        duration_ms=int((perf_counter() - started) * 1000),
                    )

        return await asyncio.gather(
            *(execute(project_id, operation) for project_id, operation in projects)
        )
