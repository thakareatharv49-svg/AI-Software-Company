from __future__ import annotations

from company.ceo.models import Decision, DecisionType, MissionPlan


class DecisionEngine:
    def decide(self, plan: MissionPlan) -> Decision:
        if not plan.objective.strip():
            return Decision(
                decision_type=DecisionType.REJECT,
                reason="Mission objective is empty",
                confidence=1.0,
            )

        if not plan.tasks:
            return Decision(
                decision_type=DecisionType.REJECT,
                reason="Mission has no executable tasks",
                confidence=1.0,
            )

        if plan.risks:
            return Decision(
                decision_type=DecisionType.ACCEPT,
                reason="Plan is executable with explicit constraints recorded",
                confidence=0.9,
            )

        return Decision(
            decision_type=DecisionType.ACCEPT,
            reason="Plan passed deterministic pre-execution validation",
            confidence=1.0,
        )
