from src.company.events.bus import CompanyEventBus
from src.company.events.events import CompanyEvent
from src.company.models.contracts import (
    CompanyCycleResult,
    CompanyMission,
    CompanyState,
)
from src.company.models.enums import CompanyDecision, CompanyStatus


class CompanyOrchestrator:
    """
    Coordinates the autonomous company lifecycle.

    The orchestrator owns state transitions but delegates actual work
    to specialized systems. It does not directly implement engineering.
    """

    def __init__(
        self,
        event_bus: CompanyEventBus | None = None,
    ) -> None:
        self.events = event_bus or CompanyEventBus()
        self.state = CompanyState()

    def start(self, mission: CompanyMission) -> CompanyCycleResult:
        if self.state.status == CompanyStatus.RUNNING:
            return CompanyCycleResult(
                decision=CompanyDecision.CONTINUE,
                message="Company is already running",
                state=self.state,
            )

        self.state.status = CompanyStatus.RUNNING
        self.state.last_decision = CompanyDecision.CONTINUE

        self.events.publish(
            CompanyEvent(
                event_type="MISSION_STARTED",
                message=f"Mission started: {mission.name}",
            )
        )

        return CompanyCycleResult(
            decision=CompanyDecision.CONTINUE,
            message="Company mission started",
            state=self.state,
        )

    def assign_project(self, project_id: str) -> CompanyCycleResult:
        if self.state.status != CompanyStatus.RUNNING:
            return CompanyCycleResult(
                decision=CompanyDecision.BLOCK,
                message="Company must be running before assigning a project",
                state=self.state,
            )

        self.state.current_project_id = project_id

        self.events.publish(
            CompanyEvent(
                event_type="PROJECT_SELECTED",
                message=f"Project selected: {project_id}",
                project_id=project_id,
            )
        )

        return CompanyCycleResult(
            decision=CompanyDecision.CONTINUE,
            message="Project assigned",
            state=self.state,
        )

    def assign_task(self, task_id: str) -> CompanyCycleResult:
        if self.state.current_project_id is None:
            return CompanyCycleResult(
                decision=CompanyDecision.BLOCK,
                message="A project must be selected before assigning a task",
                state=self.state,
            )

        self.state.current_task_id = task_id

        self.events.publish(
            CompanyEvent(
                event_type="TASK_SELECTED",
                message=f"Task selected: {task_id}",
                project_id=self.state.current_project_id,
                task_id=task_id,
            )
        )

        return CompanyCycleResult(
            decision=CompanyDecision.CONTINUE,
            message="Task assigned",
            state=self.state,
        )

    def complete_task(self) -> CompanyCycleResult:
        if self.state.current_task_id is None:
            return CompanyCycleResult(
                decision=CompanyDecision.BLOCK,
                message="No active task",
                state=self.state,
            )

        task_id = self.state.current_task_id

        self.state.completed_tasks += 1
        self.state.current_task_id = None

        self.events.publish(
            CompanyEvent(
                event_type="TASK_COMPLETED",
                message=f"Task completed: {task_id}",
                project_id=self.state.current_project_id,
                task_id=task_id,
            )
        )

        return CompanyCycleResult(
            decision=CompanyDecision.CONTINUE,
            message="Task completed; company can continue",
            state=self.state,
        )

    def complete_project(self) -> CompanyCycleResult:
        if self.state.current_project_id is None:
            return CompanyCycleResult(
                decision=CompanyDecision.BLOCK,
                message="No active project",
                state=self.state,
            )

        project_id = self.state.current_project_id

        self.state.completed_projects += 1
        self.state.current_project_id = None
        self.state.current_task_id = None
        self.state.last_decision = CompanyDecision.COMPLETE_PROJECT

        self.events.publish(
            CompanyEvent(
                event_type="PROJECT_COMPLETED",
                message=f"Project completed: {project_id}",
                project_id=project_id,
            )
        )

        return CompanyCycleResult(
            decision=CompanyDecision.COMPLETE_PROJECT,
            message="Project completed; company can select another project",
            state=self.state,
        )

    def block(self, reason: str) -> CompanyCycleResult:
        self.state.status = CompanyStatus.BLOCKED
        self.state.last_decision = CompanyDecision.BLOCK

        self.events.publish(
            CompanyEvent(
                event_type="COMPANY_BLOCKED",
                message=reason,
                project_id=self.state.current_project_id,
                task_id=self.state.current_task_id,
            )
        )

        return CompanyCycleResult(
            decision=CompanyDecision.BLOCK,
            message=reason,
            state=self.state,
        )

    def stop(self) -> CompanyCycleResult:
        self.state.status = CompanyStatus.STOPPED
        self.state.last_decision = CompanyDecision.STOP

        self.events.publish(
            CompanyEvent(
                event_type="COMPANY_STOPPED",
                message="Company execution stopped",
            )
        )

        return CompanyCycleResult(
            decision=CompanyDecision.STOP,
            message="Company execution stopped",
            state=self.state,
        )
