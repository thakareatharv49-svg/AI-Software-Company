from __future__ import annotations

from dataclasses import replace

from company.ceo.decision import DecisionEngine
from company.ceo.models import (
    CEOResult,
    DecisionType,
    Mission,
    MissionPlan,
    MissionStatus,
)
from company.ceo.planner import MissionPlanner


class AICEO:
    def __init__(
        self,
        *,
        planner: MissionPlanner | None = None,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        self.planner = planner or MissionPlanner()
        self.decision_engine = decision_engine or DecisionEngine()

    def receive(self, mission: Mission) -> Mission:
        if not mission.mission_id.strip():
            raise ValueError("Mission ID must not be empty")

        if not mission.objective.strip():
            raise ValueError("Mission objective must not be empty")

        return replace(
            mission,
            status=MissionStatus.RECEIVED,
        )

    def plan(self, mission: Mission) -> MissionPlan:
        received = self.receive(mission)
        return self.planner.plan(received)

    def decide(self, plan: MissionPlan):
        return self.decision_engine.decide(plan)

    def evaluate(self, mission: Mission) -> CEOResult:
        received = self.receive(mission)
        plan = self.planner.plan(received)
        decision = self.decision_engine.decide(plan)

        if decision.decision_type == DecisionType.ACCEPT:
            final_mission = replace(
                received,
                status=MissionStatus.APPROVED,
            )
        else:
            final_mission = replace(
                received,
                status=MissionStatus.FAILED,
            )

        return CEOResult(
            mission=final_mission,
            plan=plan,
            decision=decision,
        )
