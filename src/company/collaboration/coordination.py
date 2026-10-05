from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDependency:
    task_id: str
    depends_on: tuple[str, ...] = ()


class DependencyCoordinator:
    """Tracks dependency readiness for parallel agent work."""

    def __init__(self, dependencies: tuple[AgentDependency, ...] = ()) -> None:
        self._dependencies = {item.task_id: item for item in dependencies}
        self._completed: set[str] = set()

    def mark_complete(self, task_id: str) -> None:
        self._completed.add(task_id)

    def ready(self, task_id: str) -> bool:
        dependency = self._dependencies.get(task_id)
        return dependency is None or all(
            item in self._completed for item in dependency.depends_on
        )
