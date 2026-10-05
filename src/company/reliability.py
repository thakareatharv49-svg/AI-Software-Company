from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class IncidentSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ReliabilityEvent:
    name: str
    healthy: bool
    detail: str = ""


@dataclass(frozen=True)
class Incident:
    id: str
    severity: IncidentSeverity
    detail: str
    resolved: bool = False


@dataclass
class ReliabilityController:
    incidents: list[Incident] = field(default_factory=list)
    events: list[ReliabilityEvent] = field(default_factory=list)

    def observe(self, event: ReliabilityEvent) -> Incident | None:
        self.events.append(event)
        if event.healthy:
            return None
        severity = (
            IncidentSeverity.CRITICAL
            if "critical" in event.name.lower()
            else IncidentSeverity.WARNING
        )
        incident = Incident(str(len(self.incidents) + 1), severity, event.detail or event.name)
        self.incidents.append(incident)
        return incident

    def resolve(self, incident_id: str) -> None:
        for index, item in enumerate(self.incidents):
            if item.id == incident_id:
                self.incidents[index] = Incident(
                    item.id,
                    item.severity,
                    item.detail,
                    True,
                )
                return
        raise KeyError(incident_id)

    def health(self) -> dict[str, object]:
        open_count = sum(not incident.resolved for incident in self.incidents)
        return {
            "healthy": open_count == 0,
            "open_incidents": open_count,
            "events": len(self.events),
        }
