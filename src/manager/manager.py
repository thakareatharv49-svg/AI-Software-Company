import asyncio
from collections.abc import Callable, Sequence

from src.agents.models.contracts import AgentDefinition, AgentRequest
from src.agents.models.enums import AgentStatus
from src.agents.registry.registry import AgentRegistry
from src.manager.models.contracts import ManagerDecision, Mission, TaskPlanItem
from src.manager.models.enums import ManagerDecisionType, ManagerStatus
from src.tasks.engine.task_engine import TaskEngine
from src.tasks.models.contracts import TaskCreateRequest
from src.tasks.models.enums import TaskPriority, TaskStatus


class MasterManager:
    def __init__(
        self,
        task_engine: TaskEngine | None = None,
        agent_registry: AgentRegistry | None = None,
        agent_executor: object | None = None,
    ) -> None:
        self.task_engine = task_engine or TaskEngine()
        self.agent_registry = agent_registry or AgentRegistry()
        if not self.agent_registry.list_agents():
            from src.config.settings import settings

            self.agent_registry.register(
                AgentDefinition(
                    name="factory-engineer",
                    role="software engineer",
                    capabilities=["python", "implementation", "testing"],
                    max_concurrent_tasks=settings.factory_max_parallel_tasks,
                )
            )
        self.agent_executor = agent_executor
        self.status = ManagerStatus.IDLE
        self.mission: Mission | None = None

    def start_mission(self, mission: Mission) -> None:
        if not mission.name.strip():
            raise ValueError("Mission name cannot be empty")
        if not mission.objective.strip():
            raise ValueError("Mission objective cannot be empty")
        self.mission = mission
        self.status = ManagerStatus.PLANNING

    def create_plan(self, items: Sequence[TaskPlanItem]) -> list[str]:
        if self.mission is None:
            raise ValueError("No active mission")
        # Validate the complete dependency graph before creating any tasks.
        # Dependencies are expressed as indexes into this ordered plan, so every
        # dependency must refer to a unique task that appears earlier in the plan.
        # Silently dropping invalid indexes can make QA run too early or leave a
        # mission apparently planned while required work was never gated.
        for task_index, item in enumerate(items):
            dependencies = item.dependencies
            if len(set(dependencies)) != len(dependencies):
                raise ValueError(
                    f"Task {task_index} contains duplicate dependency indexes"
                )
            for dependency_index in dependencies:
                if type(dependency_index) is not int:
                    raise ValueError(
                        f"Task {task_index} dependency indexes must be integers"
                    )
                if dependency_index < 0 or dependency_index >= task_index:
                    raise ValueError(
                        f"Task {task_index} dependency index {dependency_index} "
                        "must reference an earlier task"
                    )

        self.status = ManagerStatus.PLANNING
        created_ids: list[str] = []
        project_id = self.mission.project_id
        for item in items:
            priority = TaskPriority(item.priority.lower())
            dependency_ids = tuple(
                created_ids[index] for index in item.dependencies
            )
            task = self.task_engine.create(
                TaskCreateRequest(
                    title=item.title,
                    description=item.description,
                    project_id=project_id,
                    priority=priority,
                    dependencies=dependency_ids,
                )
            )
            created_ids.append(task.id)
        self.status = ManagerStatus.IDLE
        return created_ids

    def choose_agent(self, task_id: str) -> str | None:
        task = self.task_engine.get(task_id)
        if task.assigned_agent:
            return task.assigned_agent
        agents = self.agent_registry.list_agents()
        available = [
            agent for agent in agents if agent.status == AgentStatus.AVAILABLE
        ]
        if not available:
            return None
        selected = available[0]
        name = getattr(selected, "name", None)
        if not name:
            return None
        self.task_engine.assign(task.id, name)
        return name

    async def _run_task(self, task_id: str, agent_name: str, runner: Callable) -> str | None:
        task = self.task_engine.get(task_id)
        try:
            result = await runner(
                AgentRequest(
                    task_id=task.id,
                    instruction=task.description or task.title,
                )
            )
            if getattr(result, "success", False):
                self.task_engine.complete(task.id)
                return None
            error = getattr(result, "error", None) or "Agent execution failed"
            self.task_engine.fail(task.id, error)
            return error
        except Exception as exc:
            self.task_engine.fail(task.id, str(exc))
            return str(exc)

    async def tick_parallel(
        self,
        *,
        executor: Callable | None = None,
        max_concurrency: int | None = None,
    ) -> ManagerDecision:
        """Execute one bounded batch of dependency-ready tasks concurrently."""
        if self.mission is None:
            return ManagerDecision(
                decision=ManagerDecisionType.BLOCK,
                reason="No active mission",
            )
        runner = executor or self.agent_executor
        if runner is None:
            return await self.tick(executor=None)

        from src.config.settings import settings

        limit = max_concurrency or settings.factory_max_parallel_tasks
        if limit < 1:
            raise ValueError("max_concurrency must be at least 1")
        limit = min(limit, settings.factory_max_parallel_tasks)

        ready = self.task_engine.ready_tasks(self.mission.project_id)
        if not ready:
            remaining = self.task_engine.list(
                project_id=self.mission.project_id,
                statuses=[
                    TaskStatus.PENDING,
                    TaskStatus.READY,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.BLOCKED,
                    TaskStatus.FAILED,
                ],
            )
            if not remaining:
                self.status = ManagerStatus.COMPLETED
                return ManagerDecision(
                    decision=ManagerDecisionType.COMPLETE_MISSION,
                    reason="All mission tasks are complete",
                )
            self.status = ManagerStatus.BLOCKED
            return ManagerDecision(
                decision=ManagerDecisionType.WAIT,
                reason="No task is currently ready",
            )

        agents = [
            agent for agent in self.agent_registry.list_agents()
            if agent.status == AgentStatus.AVAILABLE
        ]
        if not agents:
            self.status = ManagerStatus.BLOCKED
            return ManagerDecision(
                decision=ManagerDecisionType.WAIT,
                reason="No available agent",
            )

        running_counts = {
            agent.name: sum(
                1 for task in self.task_engine.list(
                    project_id=self.mission.project_id,
                    statuses=[TaskStatus.IN_PROGRESS],
                ) if task.assigned_agent == agent.name
            )
            for agent in agents
        }
        assignments: list[tuple[str, str]] = []
        for task in ready:
            if len(assignments) >= limit:
                break
            candidates = [
                agent for agent in agents
                if running_counts[agent.name] < agent.max_concurrent_tasks
            ]
            if not candidates:
                break
            agent = min(
                candidates,
                key=lambda item: running_counts[item.name],
            )
            self.task_engine.assign(task.id, agent.name)
            self.task_engine.start(task.id)
            running_counts[agent.name] += 1
            assignments.append((task.id, agent.name))

        if not assignments:
            self.status = ManagerStatus.BLOCKED
            return ManagerDecision(
                decision=ManagerDecisionType.WAIT,
                reason="All available agents are at their concurrency capacity",
            )

        self.status = ManagerStatus.EXECUTING
        results = await asyncio.gather(
            *(self._run_task(task_id, agent_name, runner) for task_id, agent_name in assignments)
        )
        self.status = ManagerStatus.IDLE
        for (task_id, agent_name), error in zip(assignments, results, strict=True):
            if error is not None:
                return ManagerDecision(
                    decision=ManagerDecisionType.WAIT,
                    reason=error,
                    task_id=task_id,
                    agent_name=agent_name,
                )
        return ManagerDecision(
            decision=ManagerDecisionType.START_TASK,
            reason=f"Executed {len(assignments)} task(s) in a bounded concurrent batch",
            task_id=assignments[0][0],
            agent_name=assignments[0][1],
        )

    async def tick(self, *, executor: Callable | None = None) -> ManagerDecision:
        if self.mission is None:
            return ManagerDecision(
                decision=ManagerDecisionType.BLOCK,
                reason="No active mission",
            )
        ready = self.task_engine.ready_tasks(self.mission.project_id)
        if not ready:
            remaining = self.task_engine.list(
                project_id=self.mission.project_id,
                statuses=[
                    TaskStatus.PENDING,
                    TaskStatus.READY,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.BLOCKED,
                    TaskStatus.FAILED,
                ],
            )
            if not remaining:
                self.status = ManagerStatus.COMPLETED
                return ManagerDecision(
                    decision=ManagerDecisionType.COMPLETE_MISSION,
                    reason="All mission tasks are complete",
                )
            self.status = ManagerStatus.BLOCKED
            return ManagerDecision(
                decision=ManagerDecisionType.WAIT,
                reason="No task is currently ready",
            )
        task = ready[0]
        agent_name = self.choose_agent(task.id)
        if agent_name is None:
            self.status = ManagerStatus.BLOCKED
            return ManagerDecision(
                decision=ManagerDecisionType.WAIT,
                reason="No available agent",
            )
        self.status = ManagerStatus.EXECUTING
        self.task_engine.start(task.id)
        runner = executor or self.agent_executor
        if runner is None:
            self.status = ManagerStatus.IDLE
            return ManagerDecision(
                decision=ManagerDecisionType.START_TASK,
                reason="Task started; execution delegated to caller",
                task_id=task.id,
                agent_name=agent_name,
            )
        error = await self._run_task(task.id, agent_name, runner)
        self.status = ManagerStatus.IDLE
        if error is not None:
            return ManagerDecision(
                decision=ManagerDecisionType.WAIT,
                reason=error,
                task_id=task.id,
                agent_name=agent_name,
            )
        return ManagerDecision(
            decision=ManagerDecisionType.START_TASK,
            reason="Task executed successfully",
            task_id=task.id,
            agent_name=agent_name,
        )
