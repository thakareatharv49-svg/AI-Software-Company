from dataclasses import dataclass

from company.production.incidents import Incident
from company.production.recovery import RecoveryPlan


@dataclass(frozen=True, slots=True)
class HealingDecision:
    incident: Incident
    action: str
    recovery: RecoveryPlan | None
    approved: bool


class ProductionSelfHealing:
    def decide(
        self, incident: Incident, recovery: RecoveryPlan
    ) -> HealingDecision:
        automatic = incident.severity in {"low", "medium"}
        return HealingDecision(
            incident,
            "recover" if automatic else "escalate",
            recovery if automatic else None,
            automatic,
        )
