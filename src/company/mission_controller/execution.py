from src.agents.execution.context import AgentExecutionContext
from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentDefinition, AgentRequest, AgentResult
from src.agents.registry.registry import AgentRegistry
from src.company.events.events import CompanyEvent
from collections.abc import Callable

from src.company.mission_controller.models import MissionPlan, MissionStage
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.mission_controller.failure_policy import (
    FailureKind,
    bounded_repair_attempts,
    classify_failure,
)


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
        self.max_repair_attempts = 2
        self.orchestrator = orchestrator
        self.executor = executor
        self.registry = registry

    def register_default_agents(self, plan: MissionPlan | None = None) -> None:
        planned_roles = {
            step.stage: step.agent_role for step in plan.steps
        } if plan is not None else {}
        for stage, name in _STAGE_AGENTS.items():
            try:
                self.registry.get(name)
            except KeyError:
                self.registry.register(
                    AgentDefinition(
                        name=name,
                        role=planned_roles.get(stage, f"{stage.value} specialist"),
                        description=f"Executes the {stage.value} mission stage.",
                        capabilities=[stage.value],
                    )
                )

    @staticmethod
    def _next_ready_step(plan: MissionPlan):
        completed = {
            step.stage.value for step in plan.steps if step.status == "completed"
        }
        return next(
            (
                step for step in plan.steps
                if step.status == "planned"
                and set(step.depends_on).issubset(completed)
            ),
            None,
        )

    async def _execute_engineering_tasks(
        self,
        mission: CompanyMission,
        plan: MissionPlan,
        step,
        on_progress: Callable[[MissionPlan], None] | None = None,
    ) -> AgentResult:
        """Execute ready engineering tasks one at a time with durable checkpoints."""
        task_agent = self.registry.get(_STAGE_AGENTS[MissionStage.EXECUTION])
        while True:
            try:
                ready = plan.ready_engineering_tasks()
            except ValueError as exc:
                return AgentResult(
                    task_id=self.orchestrator.state.current_task_id or "",
                    agent_name="mission-controller",
                    success=False,
                    error=f"Engineering task graph is invalid: {exc}",
                )

            if not ready:
                unfinished = [
                    task.id for task in plan.engineering_tasks
                    if task.status != "completed"
                ]
                if unfinished:
                    return AgentResult(
                        task_id=self.orchestrator.state.current_task_id or "",
                        agent_name="mission-controller",
                        success=False,
                        error=(
                            "Engineering task graph cannot progress; blocked or unfinished "
                            "tasks remain: " + ", ".join(unfinished)
                        ),
                    )
                return AgentResult(
                    task_id=f"task:{mission.id}:execution",
                    agent_name=task_agent.name,
                    success=True,
                )

            task = ready[0]
            task_id = f"task:{mission.id}:engineering:{task.id}"
            task.status = "running"
            task.attempts += 1
            task.detail = None
            self.orchestrator.assign_task(task_id)
            if on_progress is not None:
                on_progress(plan)
            self.orchestrator.events.publish(
                CompanyEvent(
                    event_type="ENGINEERING_TASK_STARTED",
                    message=f"Engineering task started: {task.title}",
                    project_id=f"project:{mission.id}",
                    task_id=task_id,
                )
            )

            try:
                result = await self.executor.execute(
                    AgentExecutionContext(
                        agent=task_agent,
                        allowed_permissions=frozenset(task_agent.permissions),
                    ),
                    AgentRequest(
                        task_id=task_id,
                        instruction=(
                            "Execute exactly one bounded engineering task. Do not start "
                            "tasks whose IDs are not listed as ready. Preserve the mission's "
                            "existing work and satisfy this task's acceptance check. Do not "
                            "claim tests passed unless you actually ran them.\n\n"
                            f"Task: {task.title}\n"
                            f"Requirement: {task.requirement}\n"
                            f"Workstream: {task.workstream}\n"
                            f"Assigned specialist: {task.agent_role}\n"
                            f"Acceptance check: {task.acceptance_check}\n"
                            f"Completed prerequisites: {', '.join(task.depends_on) or 'none'}"
                        ),
                        context={
                            "mission_id": mission.id,
                            "mission_name": mission.name,
                            "mission_objective": mission.objective,
                            "constraints": mission.constraints,
                            "acceptance_criteria": plan.acceptance_criteria,
                            "engineering_task": task.model_dump(mode="json"),
                            "ready_engineering_task_ids": [task.id],
                            "engineering_tasks": [
                                item.model_dump(mode="json")
                                for item in plan.engineering_task_order()
                            ],
                            "assigned_specialist": task.agent_role,
                            "stage": step.stage.value,
                        },
                    ),
                )
            except Exception as exc:
                result = AgentResult(
                    task_id=task_id,
                    agent_name=task_agent.name,
                    success=False,
                    error=f"{type(exc).__name__}: {exc}",
                )

            if not result.success:
                task.status = "failed"
                task.detail = result.error or "Engineering task execution failed"
                if on_progress is not None:
                    on_progress(plan)
                self.orchestrator.events.publish(
                    CompanyEvent(
                        event_type="ENGINEERING_TASK_FAILED",
                        message=f"Engineering task failed: {task.title}",
                        project_id=f"project:{mission.id}",
                        task_id=task_id,
                    )
                )
                return result

            task.status = "completed"
            task.detail = "Task executor returned success; overall acceptance remains subject to the QA stage."
            if on_progress is not None:
                on_progress(plan)
            self.orchestrator.events.publish(
                CompanyEvent(
                    event_type="ENGINEERING_TASK_COMPLETED",
                    message=f"Engineering task completed: {task.title}",
                    project_id=f"project:{mission.id}",
                    task_id=task_id,
                )
            )

    async def execute_next(
        self,
        mission: CompanyMission,
        plan: MissionPlan,
        on_progress: Callable[[MissionPlan], None] | None = None,
    ) -> AgentResult:
        if self.orchestrator.state.status.value != "running":
            return AgentResult(
                task_id=self.orchestrator.state.current_task_id or "",
                agent_name="mission-controller",
                success=False,
                error="Company must be running before executing a stage",
            )

        # Reject malformed engineering DAGs before any agent or tool work starts.
        # Empty task lists remain compatible with legacy persisted plans.
        if plan.engineering_tasks:
            try:
                plan.engineering_task_order()
            except ValueError as exc:
                error = f"Engineering task graph is invalid: {exc}"
                self.orchestrator.block(error)
                return AgentResult(
                    task_id=self.orchestrator.state.current_task_id or "",
                    agent_name="mission-controller",
                    success=False,
                    error=error,
                )

        self.register_default_agents(plan)

        step = self._next_ready_step(plan)
        if step is None and any(item.status == "planned" for item in plan.steps):
            completed = {
                item.stage.value for item in plan.steps if item.status == "completed"
            }
            unresolved = [
                f"{item.stage.value} requires {', '.join(item.depends_on)}"
                for item in plan.steps
                if item.status == "planned"
                and not set(item.depends_on).issubset(completed)
            ]
            error = "Mission plan has no dependency-ready stage: " + "; ".join(unresolved)
            self.orchestrator.block(error)
            return AgentResult(
                task_id=self.orchestrator.state.current_task_id or "",
                agent_name="mission-controller",
                success=False,
                error=error,
            )
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

        result: AgentResult | None = None
        if step.stage == MissionStage.EXECUTION and plan.engineering_tasks:
            result = await self._execute_engineering_tasks(
                mission, plan, step, on_progress=on_progress
            )
            if not result.success:
                step.status = "failed"
                step.detail = result.error or "Engineering task execution failed"
                self.orchestrator.block(step.detail)
                self.orchestrator.events.publish(
                    CompanyEvent(
                        event_type="STAGE_FAILED",
                        message=f"Stage failed: {step.stage.value}: {step.detail}",
                        project_id=self.orchestrator.state.current_project_id,
                        task_id=result.task_id,
                    )
                )
                return result
        else:
            last_error = ""
            repair_limit = bounded_repair_attempts(self.max_repair_attempts)
            max_attempts = repair_limit + 1
            for attempt in range(1, max_attempts + 1):
                step.attempts += 1
                repair_instruction = step.objective
                if attempt > 1:
                    previous_kind = classify_failure(last_error)
                    if previous_kind == FailureKind.TRANSIENT:
                        retry_guidance = (
                            "TRANSIENT FAILURE RETRY: The previous attempt appears "
                            "to have failed due to a temporary service or network issue. "
                            "Retry the same task without changing unrelated code. "
                        )
                    else:
                        retry_guidance = (
                            "AUTOMATED REPAIR RETRY: Diagnose the specific failure, "
                            "make the smallest safe correction, and verify the correction. "
                        )
                    repair_instruction = (
                        f"{step.objective}\n\n"
                        + retry_guidance
                        + "Do not claim a check passed unless you actually verified it.\n"
                        + f"Previous failure: {last_error}\n"
                        + f"Failure category: {previous_kind.value}\n"
                        + f"Repair attempt: {attempt - 1} of {repair_limit}"
                    )

                try:
                    result = await self.executor.execute(
                        AgentExecutionContext(
                            agent=agent,
                            allowed_permissions=frozenset(agent.permissions),
                        ),
                        AgentRequest(
                            task_id=task_id,
                            instruction=repair_instruction,
                            context={
                                "mission_id": mission.id,
                                "mission_name": mission.name,
                                "mission_objective": mission.objective,
                                "constraints": mission.constraints,
                                "acceptance_criteria": plan.acceptance_criteria,
                                # Send tasks in validated dependency-first order. The
                                # explicit ready IDs prevent the execution agent from
                                # treating blocked descendants as immediately executable.
                                "engineering_tasks": [
                                    task.model_dump(mode="json")
                                    for task in plan.engineering_task_order()
                                ],
                                "ready_engineering_task_ids": [
                                    task.id for task in plan.ready_engineering_tasks()
                                ],
                                "assigned_specialist": step.agent_role,
                                "dependencies": step.depends_on,
                                "stage": step.stage.value,
                                "repair_attempt": attempt - 1,
                                "repair_attempt_limit": self.max_repair_attempts,
                                "previous_failure": last_error or None,
                                "qa_expectations": (
                                    [
                                        "Report the exact checks performed.",
                                        "Distinguish passed, failed, and unrun checks.",
                                        "For every failure, include a reproducible diagnosis and proposed correction.",
                                        "Do not report success when required checks were not run.",
                                    ]
                                    if step.stage == MissionStage.QA
                                    else []
                                ),
                            },
                        ),
                    )
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    result = AgentResult(
                        task_id=task_id,
                        agent_name=agent_name,
                        success=False,
                        error=error,
                    )

                if result.success:
                    break

                last_error = result.error or "Agent execution failed without an error detail"
                failure_kind = classify_failure(last_error)
                # Do not spend repair attempts on provider/configuration failures:
                # a prompt cannot fix credentials, permissions, quotas, or cooldowns.
                if failure_kind == FailureKind.NON_RETRYABLE:
                    break
                if attempt < max_attempts:
                    self.orchestrator.events.publish(
                        CompanyEvent(
                            event_type="STAGE_REPAIR_STARTED",
                            message=(
                                f"Repair retry {attempt}/{self.max_repair_attempts} "
                                f"for stage: {step.stage.value}: {last_error}"
                            ),
                            project_id=self.orchestrator.state.current_project_id,
                            task_id=task_id,
                        )
                    )

        assert result is not None
        if not result.success:
            step.status = "failed"
            step.detail = (
                last_error
                if attempt == 1
                else f"Failed after {attempt} attempt(s): {last_error}"
            )
            self.orchestrator.block(step.detail)
            self.orchestrator.events.publish(
                CompanyEvent(
                    event_type="STAGE_FAILED",
                    message=f"Stage failed: {step.stage.value}: {step.detail}",
                    project_id=self.orchestrator.state.current_project_id,
                    task_id=task_id,
                )
            )
            return AgentResult(
                task_id=task_id,
                agent_name=agent_name,
                success=False,
                error=step.detail,
            )

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

        next_step = self._next_ready_step(plan)
        if next_step is None and any(item.status == "planned" for item in plan.steps):
            error = "Mission plan has remaining stages with unresolved dependencies"
            self.orchestrator.block(error)
            return AgentResult(
                task_id=task_id,
                agent_name=agent_name,
                success=False,
                error=error,
            )
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
        on_progress: Callable[[MissionPlan], None] | None = None,
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
            result = await self.execute_next(mission, plan, on_progress=on_progress)
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
