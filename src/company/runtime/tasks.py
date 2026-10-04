from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RuntimeTask:
    task_id: str
    state: str


class RuntimeTaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, RuntimeTask] = {}
        self._lock = asyncio.Lock()

    async def register(self, task_id: str) -> RuntimeTask:
        if not task_id:
            raise ValueError("task_id must not be empty")

        async with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"task already registered: {task_id}")

            task = RuntimeTask(task_id=task_id, state="pending")
            self._tasks[task_id] = task
            return task

    async def update(self, task_id: str, state: str) -> RuntimeTask:
        if not state:
            raise ValueError("state must not be empty")

        async with self._lock:
            if task_id not in self._tasks:
                raise KeyError(task_id)

            task = RuntimeTask(task_id=task_id, state=state)
            self._tasks[task_id] = task
            return task

    async def get(self, task_id: str) -> RuntimeTask | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def list(self) -> list[RuntimeTask]:
        async with self._lock:
            return list(self._tasks.values())

    async def remove(self, task_id: str) -> None:
        async with self._lock:
            self._tasks.pop(task_id, None)


class RuntimeTaskExecutor:
    def __init__(self, registry: RuntimeTaskRegistry) -> None:
        self.registry = registry

    async def execute(
        self,
        task_id: str,
        operation: Callable[[], Awaitable[object]],
    ) -> object:
        await self.registry.register(task_id)
        await self.registry.update(task_id, "running")

        try:
            result = await operation()
        except asyncio.CancelledError:
            await self.registry.update(task_id, "cancelled")
            raise
        except Exception:
            await self.registry.update(task_id, "failed")
            raise
        else:
            await self.registry.update(task_id, "completed")
            return result
