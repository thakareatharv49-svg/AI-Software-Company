from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True, slots=True)
class AgentWorkItem:
    task_id: str
    agent_name: str
    payload: Any


@dataclass(frozen=True, slots=True)
class AgentWorkResult:
    task_id: str
    agent_name: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: int = 0


AgentWorker = Callable[[AgentWorkItem], Awaitable[Any]]


class AgentWorkerPool:
    """Bounded concurrent workforce with per-task failure isolation."""

    def __init__(self, worker: AgentWorker, max_concurrency: int = 4) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        self.worker = worker
        self.max_concurrency = max_concurrency

    async def execute(self, items: list[AgentWorkItem]) -> list[AgentWorkResult]:
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run(item: AgentWorkItem) -> AgentWorkResult:
            started = time.perf_counter()
            async with semaphore:
                try:
                    output = await self.worker(item)
                    return AgentWorkResult(
                        item.task_id,
                        item.agent_name,
                        True,
                        output,
                        duration_ms=int((time.perf_counter() - started) * 1000),
                    )
                except Exception as exc:
                    return AgentWorkResult(
                        item.task_id,
                        item.agent_name,
                        False,
                        error=str(exc),
                        duration_ms=int((time.perf_counter() - started) * 1000),
                    )

        return await asyncio.gather(*(run(item) for item in items))
