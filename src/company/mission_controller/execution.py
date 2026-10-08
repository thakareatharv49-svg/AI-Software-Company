from src.agents.execution.context import AgentExecutionContext
from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentDefinition, AgentRequest, AgentResult
from src.agents.registry.registry import AgentRegistry
from src.company.events.events import CompanyEvent
from src.company.mission_controller.models import MissionPlan, MissionStage
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator


_STAGE_AGENTS: dict[MissionStage, str] = {
    stage: f"{stage.value}-agent" for stage in MissionStage
}


class MissionExecutionPipeline:
    """Executes planned mission stages through the existing agent engine."""

    def __init__(
        self,
        orchestrator: CompanyOrchestrator,
        executor: AgentExecutor,
        registry: AgentRegistry,
    ) -> None:
        self.orchestrator = orchestrator
        self.executor = executor
        self.registry = registry

    def register_default_agents(self) -> None:
        for stage, name in _STAGE_AGENTS.items():
            try:
                self.registry.get(name)
            except KeyError:
                self.registry.register(
                    AgentDefinition(
                        name=name,
                        role=f"{stage.value} specialist",
                        description=f"Executes the {stage.value} mission stage.",
                        capabilities=[stage.value],
                    )
                )

    async def execute_next(
        self,
        mission: CompanyMission,
        plan: MissionPlan,
    ) -> AgentResult:
        if self.orchestrator.state.status.value != "running":
            return AgentResult(
                task_id=self.orchestrator.state.current_task_id or "",
                agent_name="mission-controller",
                success=False,
                error="Company must be running before executing a stage",
            )

        self.register_default_agents()

        step = next((item for item in plan.steps if item.status == "planned"), None)
        if step is None:
            return AgentResult(
                task_id=self.orchestrator.state.current_task_id or "",
                agent_name="mission-controller",
                success=False,
                error="No planned stages remain",
            )

        task_id = f"task:{mission.id}:{step.stage.value}"
        if self.orchestrator.state.current_task_id != task_id:
            self.orchestrator.assign_task(task_id)

        step.status = "running"
        agent_name = _STAGE_AGENTS[step.stage]
        agent = self.registry.get(agent_name)

        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="STAGE_STARTED",
                message=f"Stage started: {step.stage.value}",
                project_id=self.orchestrator.state.current_project_id,
                task_id=task_id,
            )
        )

        result = await self.executor.execute(
            AgentExecutionContext(
                agent=agent,
                allowed_permissions=frozenset(agent.permissions),
            ),
            AgentRequest(
                task_id=task_id,
                instruction=step.objective,
                context={
                    "mission_id": mission.id,
                    "mission_name": mission.name,
                    "mission_objective": mission.objective,
                    "constraints": mission.constraints,
                    "stage": step.stage.value,
                },
            ),
        )

        if not result.success:
            step.status = "failed"
            self.orchestrator.block(result.error or "Agent execution failed")
            self.orchestrator.events.publish(
                CompanyEvent(
                    event_type="STAGE_FAILED",
                    message=f"Stage failed: {step.stage.value}: {result.error}",
                    project_id=self.orchestrator.state.current_project_id,
                    task_id=task_id,
                )
            )
            return result

        step.status = "completed"
        self.orchestrator.complete_task()
        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="STAGE_COMPLETED",
                message=f"Stage completed: {step.stage.value}",
                project_id=self.orchestrator.state.current_project_id,
                task_id=task_id,
            )
        )

        next_step = next((item for item in plan.steps if item.status == "planned"), None)
        if next_step is None:
            self.orchestrator.complete_project()
            self.orchestrator.events.publish(
                CompanyEvent(
                    event_type="MISSION_PIPELINE_COMPLETED",
                    message=f"Mission pipeline completed: {mission.name}",
                    project_id=f"project:{mission.id}",
                )
            )
            return result

        next_task_id = f"task:{mission.id}:{next_step.stage.value}"
        self.orchestrator.assign_task(next_task_id)
        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="STAGE_READY",
                message=f"Next stage ready: {next_step.stage.value}",
                project_id=self.orchestrator.state.current_project_id,
                task_id=next_task_id,
            )
        )
        return result

    async def execute_mission(
        self,
        mission: CompanyMission,
        plan: MissionPlan,
        max_stages: int | None = None,
    ) -> list[AgentResult]:
        """Continuously execute planned stages until completion or a safe stop."""
        results: list[AgentResult] = []
        completed = 0
        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="MISSION_EXECUTION_STARTED",
                message=f"Autonomous execution started: {mission.name}",
                project_id=self.orchestrator.state.current_project_id,
            )
        )

        while self.orchestrator.state.status.value == "running":
            if max_stages is not None and completed >= max_stages:
                break
            result = await self.execute_next(mission, plan)
            results.append(result)
            if not result.success:
                break
            completed += 1
            if (
                self.orchestrator.state.last_decision is not None
                and self.orchestrator.state.last_decision.value == "complete_project"
            ):
                break

        if self.orchestrator.state.status.value == "running" and completed == 0:
            self.orchestrator.block("Autonomous execution made no progress")

        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="MISSION_EXECUTION_STOPPED",
                message=f"Autonomous execution stopped after {completed} stage(s)",
                project_id=self.orchestrator.state.current_project_id,
            )
        )
        return results
