from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class InfrastructurePlan:
    service: str
    environment: str
    resources: tuple[str, ...]

class InfrastructureService:
    def plan(self, service: str, environment: str, resources: list[str]) -> InfrastructurePlan:
        if not service.strip() or not environment.strip():
            raise ValueError("service and environment must not be empty")
        return InfrastructurePlan(service, environment, tuple(resources))
