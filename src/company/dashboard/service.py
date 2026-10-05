from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DashboardSnapshot:
    company: dict[str, object]
    projects: tuple[dict[str, object], ...] = ()
    agents: tuple[dict[str, object], ...] = ()
    tasks: tuple[dict[str, object], ...] = ()
    runtime: dict[str, object] = field(default_factory=dict)
    memory: dict[str, object] = field(default_factory=dict)
    qa: dict[str, object] = field(default_factory=dict)
    security: dict[str, object] = field(default_factory=dict)
    costs: dict[str, object] = field(default_factory=dict)
    deployments: dict[str, object] = field(default_factory=dict)
    failures: tuple[dict[str, object], ...] = ()
    research: tuple[dict[str, object], ...] = ()
    metrics: dict[str, object] = field(default_factory=dict)
    audit: tuple[dict[str, object], ...] = ()


class CompanyDashboard:
    """Read-only aggregation boundary for company operational state."""

    def __init__(self, providers: dict[str, Callable[[], object]] | None = None) -> None:
        self._providers = dict(providers or {})

    def snapshot(self) -> DashboardSnapshot:
        def read(name: str, default: object) -> object:
            provider = self._providers.get(name)
            return provider() if provider is not None else default

        return DashboardSnapshot(
            company=dict(read("company", {})),
            projects=tuple(read("projects", ())),
            agents=tuple(read("agents", ())),
            tasks=tuple(read("tasks", ())),
            runtime=dict(read("runtime", {})),
            memory=dict(read("memory", {})),
            qa=dict(read("qa", {})),
            security=dict(read("security", {})),
            costs=dict(read("costs", {})),
            deployments=dict(read("deployments", {})),
            failures=tuple(read("failures", ())),
            research=tuple(read("research", ())),
            metrics=dict(read("metrics", {})),
            audit=tuple(read("audit", ())),
        )

    def health(self) -> dict[str, object]:
        snapshot = self.snapshot()
        return {
            "projects": len(snapshot.projects),
            "agents": len(snapshot.agents),
            "tasks": len(snapshot.tasks),
            "failures": len(snapshot.failures),
            "research_reports": len(snapshot.research),
        }
