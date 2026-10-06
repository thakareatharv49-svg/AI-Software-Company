from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CodingPlan:
    task: str
    steps: tuple[str, ...]


class CodingAgent:
    """Plans bounded coding work and delegates execution to an injected executor."""

    def plan(self, task: str) -> CodingPlan:
        task = " ".join(task.split()).strip()
        if not task:
            raise ValueError("task must not be empty")
        return CodingPlan(task, ("inspect", "implement", "test", "review"))

    def execute(
        self,
        plan: CodingPlan,
        executor: Callable[[str], object],
    ) -> tuple[object, ...]:
        return tuple(executor(step) for step in plan.steps)
