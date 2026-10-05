from __future__ import annotations

from company.ceo.models import Mission, MissionPlan


class MissionPlanner:
    def plan(self, mission: Mission) -> MissionPlan:
        objective = mission.objective.strip()

        if not objective:
            raise ValueError("Mission objective must not be empty")

        goals = (
            f"Define a successful outcome for: {objective}",
            "Validate constraints and risks before execution",
            "Produce a verifiable implementation result",
        )

        tasks = (
            "Analyze mission requirements",
            "Identify dependencies and constraints",
            "Design the execution approach",
            "Break the work into executable tasks",
            "Validate the plan before execution",
        )

        risks = tuple(
            constraint
            for constraint in mission.constraints
            if constraint.strip()
        )

        return MissionPlan(
            mission_id=mission.mission_id,
            objective=objective,
            goals=goals,
            tasks=tasks,
            risks=risks,
            assumptions=("Execution must pass quality gates",),
        )
