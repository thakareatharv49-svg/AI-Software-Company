from collections.abc import Callable, Sequence

from src.agents.models.contracts import AgentRequest
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

        self.status = ManagerStatus.PLANNING
        created_ids: list[str] = []
        project_id = self.mission.project_id

        for item in items:
            priority = TaskPriority(item.priority.lower())
            dependency_ids = tuple(
                created_ids[index]
                for index in item.dependencies
                if 0 <= index < len(created_ids)
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
            agent
            for agent in agents
            if agent.status == AgentStatus.AVAILABLE
        ]

        if not available:
            return None

        selected = available[0]
        name = getattr(selected, "name", None)

        if not name:
            return None

        self.task_engine.assign(task.id, name)
        return name

    async def tick(
        self,
        *,
        executor: Callable | None = None,
    ) -> ManagerDecision:
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

        try:
            result = await runner(
                AgentRequest(
                    task_id=task.id,
                    instruction=task.description or task.title,
                )
            )

            if getattr(result, "success", False):
                self.task_engine.complete(task.id)
                self.status = ManagerStatus.IDLE
                return ManagerDecision(
                    decision=ManagerDecisionType.START_TASK,
                    reason="Task executed successfully",
                    task_id=task.id,
                    agent_name=agent_name,
                )

            error = getattr(result, "error", None) or "Agent execution failed"
            self.task_engine.fail(task.id, error)
            self.status = ManagerStatus.IDLE

            return ManagerDecision(
                decision=ManagerDecisionType.WAIT,
                reason=error,
                task_id=task.id,
                agent_name=agent_name,
            )

        except Exception as exc:
            self.task_engine.fail(task.id, str(exc))
            self.status = ManagerStatus.IDLE
            return ManagerDecision(
                decision=ManagerDecisionType.WAIT,
                reason=str(exc),
                task_id=task.id,
                agent_name=agent_name,
            )

