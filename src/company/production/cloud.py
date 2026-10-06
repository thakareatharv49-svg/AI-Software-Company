from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class CloudDeployment:
    service: str
    environment: str
    version: str
    status: str

class CloudDeploymentService:
    def deploy(self, service: str, environment: str, version: str) -> CloudDeployment:
        if not version.strip():
            raise ValueError("version must not be empty")
        return CloudDeployment(service, environment, version, "requested")
