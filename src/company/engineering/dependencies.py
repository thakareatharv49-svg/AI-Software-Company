from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Dependency:
    name: str
    current: str
    target: str | None = None
    latest: str | None = None


class DependencyManager:
    """Tracks dependency state and flags upgrades without package installation."""

    def outdated(self, dependencies: list[Dependency]) -> tuple[Dependency, ...]:
        return tuple(
            item for item in dependencies if item.latest and item.latest != item.current
        )

    def plan(self, dependency: Dependency) -> str:
        target = dependency.target or dependency.latest or dependency.current
        return f"upgrade {dependency.name} from {dependency.current} to {target}"
