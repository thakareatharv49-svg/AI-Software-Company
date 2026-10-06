from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Incident:
    service: str
    severity: str
    summary: str
    status: str = "open"

class IncidentService:
    def create(self, service: str, severity: str, summary: str) -> Incident:
        if severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("invalid severity")
        return Incident(service, severity, summary)
