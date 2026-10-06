from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    service: str
    target_version: str
    action: str

class RecoveryService:
    def rollback(self, service: str, target_version: str) -> RecoveryPlan:
        if not target_version.strip():
            raise ValueError("target_version must not be empty")
        return RecoveryPlan(service, target_version, "rollback")
