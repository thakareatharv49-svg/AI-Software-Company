from src.company.events.events import CompanyEvent
from src.company.mission_controller.models import MissionPlan
from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyCycleResult, CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator


class MissionController:
    """Turns a human mission into an internal company execution plan."""

    def __init__(self, orchestrator: CompanyOrchestrator) -> None:
        self.orchestrator = orchestrator
        self._plans: dict[str, MissionPlan] = {}

    def prepare(self, mission: CompanyMission) -> MissionPlan:
        """Build and register a mission plan without starting execution."""
        plan = build_mission_plan(mission)
        self._plans[mission.id] = plan
        return plan

    def start(self, mission: CompanyMission) -> tuple[MissionPlan, CompanyCycleResult]:
        plan = self.prepare(mission)

        result = self.orchestrator.start(mission)
        if result.state.status.value != "running":
            return plan, result

        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="MISSION_PLANNED",
                message=(
                    f"Mission plan created: {mission.name} "
                    f"({len(plan.steps)} stages)"
                ),
            )
        )

        project_id = f"project:{mission.id}"
        result = self.orchestrator.assign_project(project_id)
        if result.decision.value == "block":
            return plan, result

        task_id = f"task:{mission.id}:{plan.steps[0].stage.value}"
        result = self.orchestrator.assign_task(task_id)

        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="MISSION_PIPELINE_READY",
                message=(
                    f"Pipeline ready: {plan.steps[0].stage.value} "
                    "is the first executable stage"
                ),
                project_id=project_id,
                task_id=task_id,
            )
        )
        return plan, result

    def get_plan(self, mission_id: str) -> MissionPlan | None:
        return self._plans.get(mission_id)
