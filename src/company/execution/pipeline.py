from collections.abc import Callable
from dataclasses import dataclass, replace
from src.agents.execution.context import AgentExecutionContext
from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentRequest, AgentResult
from src.company.gates.quality import ProductionQualityGate
from src.company.project_generator import OllamaProjectGenerator
from src.config.settings import settings
from src.company.github_native.service import GitHubNativeService
from src.company.intelligence import (
    CrossProjectMemory,
    LearningEngine,
    LearningSignal,
    MemoryInsight,
)
from src.company.observability.service import ObservabilityService
from src.company.recovery.service import RecoveryService
from src.events.models.contracts import CompanyEvent
from src.events.service.factory import get_event_service
from src.github.automation.automation import GitHubAutomation
from src.github.client.http import GitHubHttpClient
from src.github.models.contracts import GitHubRepository
from src.manager.manager import MasterManager
from src.manager.models.contracts import Mission, TaskPlanItem
from src.memory.models.contracts import MemoryCreateRequest
from src.memory.models.enums import MemoryType
from src.memory.service.service import MemoryService
from src.projects.engine.project_engine import ProjectEngine
from src.projects.models.contracts import Project, ProjectCreateRequest
from src.projects.models.enums import ProjectStatus
from src.qa.debugging.debugger import AutonomousDebugger
from src.qa.execution.runner import QARunner
from src.qa.models.contracts import QATestRequest, QATestResult
from src.qa.models.enums import DebugStatus, QATestStatus
from src.security.models.contracts import CodeReviewRequest, CodeReviewResult
from src.security.review.reviewer import CodeReviewer


@dataclass(slots=True)
class PipelineResult:
    project: Project
    task_ids: list[str]
    qa_result: QATestResult
    review_result: CodeReviewResult
    github_message: str | None = None
    memory_id: str | None = None


class CompanyExecutionPipeline:
    def __init__(
        self,
        *,
        project_engine: ProjectEngine | None = None,
        manager: MasterManager | None = None,
        qa_runner: QARunner | None = None,
        debugger: AutonomousDebugger | None = None,
        reviewer: CodeReviewer | None = None,
        github: GitHubAutomation | None = None,
        github_native: GitHubNativeService | None = None,
        memory: MemoryService | None = None,
        cross_project_memory: CrossProjectMemory | None = None,
        learning: LearningEngine | None = None,
        project_generator: OllamaProjectGenerator | None = None,
    ) -> None:
        self.event_service = get_event_service()
        self.project_engine = project_engine or ProjectEngine()
        self.manager = manager or MasterManager()
        self.qa_runner = qa_runner or QARunner()
        self.debugger = debugger or AutonomousDebugger(
            qa_runner=self.qa_runner,
        )
        self.reviewer = reviewer or CodeReviewer()
        configured_github = None
        configured_github_native = None
        if (
            settings.github_allow_writes
            and settings.github_token
            and settings.github_repository_owner
        ):
            github_client = GitHubHttpClient(
                token=settings.github_token,
                api_url=settings.github_api_base_url,
            )
            configured_github = GitHubAutomation(github_client)
            configured_github_native = GitHubNativeService(
                github=configured_github,
            )

        self.github = github or configured_github
        self.github_native = github_native or configured_github_native
        self.memory = memory or MemoryService()
        self.cross_project_memory = cross_project_memory or CrossProjectMemory()
        self.learning = learning or LearningEngine()
        self.project_generator = project_generator or OllamaProjectGenerator()
        self._active_generated_files: dict[str, str] = {}
        self.recovery = RecoveryService(max_attempts=1)
        self.quality_gate = ProductionQualityGate()
        self.observability = ObservabilityService()
        self._active_run_id: str | None = None

    def _publish_event(
        self,
        event_type: str,
        *,
        project_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        event_payload = dict(payload or {})

        if self._active_run_id is not None:
            event_payload.setdefault("run_id", self._active_run_id)
            self.observability.record(
                run_id=self._active_run_id,
                event_type=event_type,
                project_id=project_id,
                payload=event_payload,
            )

        event = CompanyEvent(
            event_type=event_type,
            project_id=project_id,
            payload=event_payload,
        )
        self.event_service.publish(event)

    async def execute(
        self,
        *,
        project_request: ProjectCreateRequest,
        mission: Mission,
        tasks: list[TaskPlanItem],
        qa_request: QATestRequest,
        files: dict[str, str],
        agent_executor: Callable | AgentExecutor | None = None,
        repair_agent_executor: Callable | AgentExecutor | None = None,
        github_repository: GitHubRepository | None = None,
        pull_request_head: str | None = None,
    ) -> PipelineResult:
        self._active_generated_files = files
        project = self.project_engine.create(project_request)

        self._publish_event(
            "project.execution.started",
            project_id=project.id,
            payload={
                "project_name": project.name,
                "objective": project.objective,
            },
        )
        project = self._transition_to_development(project)
        mission = replace(mission, project_id=project.id)

        self.manager.start_mission(mission)
        task_ids = self.manager.create_plan(tasks)

        executor = self._build_executor(agent_executor)
        await self._execute_tasks(executor)

        project = self.project_engine.transition(
            project.id,
            ProjectStatus.TESTING,
        )

        repair_callback = self._build_repair_callback(
            repair_agent_executor or agent_executor
        )

        debug_result = await self.debugger.run(
            qa_request,
            repair=repair_callback,
        )

        if debug_result.attempts:
            latest_attempt = debug_result.attempts[-1]

            if latest_attempt.test_status != QATestStatus.PASSED:
                self._publish_event(
                    "qa.failed",
                    project_id=project.id,
                    payload={
                        "attempt": latest_attempt.attempt,
                        "error": latest_attempt.error,
                        "status": latest_attempt.test_status.value,
                    },
                )

        if debug_result.status == DebugStatus.BLOCKED:
            self.project_engine.transition(
                project.id,
                ProjectStatus.DEBUGGING,
            )
            raise RuntimeError(
                f"QA failed for project {project.id}: "
                f"{debug_result.final_error}"
            )

        qa_result = await self.qa_runner.run(qa_request)

        if qa_result.status != QATestStatus.PASSED:
            self.project_engine.transition(
                project.id,
                ProjectStatus.DEBUGGING,
            )
            raise RuntimeError(
                f"QA failed for project {project.id}: "
                f"{qa_result.stderr or qa_result.stdout}"
            )

        self.project_engine.transition(
            project.id,
            ProjectStatus.SECURITY,
        )

        review_result = self.reviewer.review(
            CodeReviewRequest(
                project_id=project.id,
                task_id=task_ids[-1] if task_ids else None,
                working_directory=qa_request.working_directory,
                files=files,
                diff="\n".join(
                    f"--- {path}\n+++ {path}\n{content}"
                    for path, content in files.items()
                ),
            )
        )

        if review_result.status.value != "approved":
            self.project_engine.transition(
                project.id,
                ProjectStatus.DEBUGGING,
            )
            raise RuntimeError(
                f"Code review failed for project {project.id}: "
                f"{review_result.summary}"
            )

        self.project_engine.transition(project.id, ProjectStatus.REVIEW)

        gate = self.quality_gate.evaluate(
            qa_passed=qa_result.status == QATestStatus.PASSED,
            security_approved=review_result.status.value == "approved",
            github_ready=(
                self.github is not None
                and github_repository is not None
                and pull_request_head is not None
            ) or (
                self.github is None
                and github_repository is None
                and pull_request_head is None
            ),
            deployment_ready=True,
        )
        self._publish_event(
            "production.gate.evaluated",
            project_id=project.id,
            payload={"allowed": gate.allowed, "checks": gate.checks},
        )
        if not gate.allowed:
            self.project_engine.transition(project.id, ProjectStatus.BLOCKED)
            raise RuntimeError(gate.reason)

        github_message = None

        if (
            self.github is not None
            and github_repository is not None
            and pull_request_head is not None
        ):
            if self.github_native is not None:
                publish_result = await self.github_native.publish_files(
                    github_repository,
                    pull_request_head,
                    files,
                    f"feat: complete {project.name}",
                )
                if not publish_result.success:
                    raise RuntimeError(publish_result.message)

            github_message = f"Published generated project directly to {github_repository.owner}/{github_repository.name}:{pull_request_head}"

        self.project_engine.transition(project.id, ProjectStatus.RELEASE)
        project = self.project_engine.complete(project.id)

        memory_entry = self.memory.remember(
            MemoryCreateRequest(
                memory_type=MemoryType.PROJECT,
                title=f"Completed project: {project.name}",
                content=(
                    f"Project {project.name} completed successfully. "
                    f"Tasks completed: {len(task_ids)}."
                ),
                project_id=project.id,
            )
        )

        self.cross_project_memory.remember(MemoryInsight(
            key="completed-project",
            value=(
                f"{project.name}: completed with {len(task_ids)} tasks; "
                f"QA={qa_result.status.value}; security={review_result.status.value}."
            ),
            project_id=project.id,
            importance=1.0,
        ))
        self.learning.record(LearningSignal(
            category="project-execution",
            outcome="completed",
            value=1.0,
            project_id=project.id,
        ))
        self._publish_event(
            "company.intelligence.learned",
            project_id=project.id,
            payload={"category": "project-execution", "outcome": "completed"},
        )

        self._publish_event(
            "project.execution.completed",
            project_id=project.id,
            payload={
                "status": project.status.value,
            },
        )

        return PipelineResult(
            project=project,
            task_ids=task_ids,
            qa_result=qa_result,
            review_result=review_result,
            github_message=github_message,
            memory_id=memory_entry.id,
        )

    async def run_end_to_end(
        self,
        *,
        project_request: ProjectCreateRequest,
        mission: Mission,
        tasks: list[TaskPlanItem],
        qa_request: QATestRequest,
        files: dict[str, str],
        agent_executor: Callable | AgentExecutor | None = None,
        repair_agent_executor: Callable | AgentExecutor | None = None,
        github_repository: GitHubRepository | None = None,
        pull_request_head: str | None = None,
    ) -> PipelineResult:
        """
        Execute one complete autonomous company run.

        This is the public M15 entry point. The existing execute()
        method remains the authoritative project execution workflow.
        """

        self._active_run_id = self.observability.create_run_id()

        while True:
            try:
                result = await self.execute(
                    project_request=project_request,
                    mission=mission,
                    tasks=tasks,
                    qa_request=qa_request,
                    files=files,
                    agent_executor=agent_executor,
                    repair_agent_executor=repair_agent_executor,
                    github_repository=github_repository,
                    pull_request_head=pull_request_head,
                )

                self.recovery.reset()

                self._publish_event(
                    "autonomous.run.completed",
                    project_id=result.project.id,
                    payload={
                        "status": "completed",
                        "task_count": len(result.task_ids),
                    },
                )

                return result

            except Exception as exc:
                recovery = self.recovery.record_failure(error=exc)

                self._publish_event(
                    "autonomous.run.failed",
                    project_id=recovery.project_id,
                    payload={
                        "status": "failed",
                        "error": str(exc),
                        "project_name": project_request.name,
                        "recovery_action": recovery.action,
                        "retryable": recovery.retryable,
                        "attempt": recovery.attempt,
                    },
                )

                if not recovery.retryable:
                    self.recovery.reset()
                    raise

                self._publish_event(
                    "autonomous.run.recovery_available",
                    project_id=recovery.project_id,
                    payload={
                        "action": recovery.action,
                        "attempt": recovery.attempt,
                    },
                )

    def _select_repair_agent(self) -> str:
        agents = self.manager.agent_registry.list_agents()

        preferred = (
            "backend-engineer",
            "ai-engineer",
            "infrastructure-engineer",
            "database-engineer",
            "frontend-engineer",
        )

        available = {agent.name for agent in agents}

        for name in preferred:
            if name in available:
                return name

        if agents:
            return agents[0].name

        raise RuntimeError("No repair agent is registered")

    def _build_repair_callback(
        self,
        executor: Callable | AgentExecutor | None,
    ) -> Callable | None:
        if executor is None:
            async def generated_project_repair(request: QATestRequest, diagnosis) -> bool:
                repaired = await self.project_generator.repair(
                    files=self._active_generated_files,
                    failure=diagnosis.error,
                )
                self._active_generated_files.clear()
                self._active_generated_files.update(repaired.files)
                root = Path(request.working_directory)
                for path, content in repaired.files.items():
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                return True

            return generated_project_repair

        if isinstance(executor, AgentExecutor):
            executor = self._agent_executor_adapter(executor)

        async def repair(
            request: QATestRequest,
            diagnosis,
        ) -> bool:
            result = await executor(
                AgentRequest(
                    task_id=f"qa-repair-{diagnosis.attempt}",
                    instruction=(
                        "Repair the current QA failure autonomously. "
                        "Inspect the failure, locate the faulty code, "
                        "modify the workspace using permitted tools, and "
                        "run the relevant test or command to verify the fix."
                    ),
                    context={
                        "qa_command": request.command,
                        "working_directory": request.working_directory,
                        "failure": diagnosis.error,
                        "stdout": diagnosis.stdout,
                        "stderr": diagnosis.stderr,
                    },
                )
            )

            if isinstance(result, AgentResult):
                return result.success

            if isinstance(result, bool):
                return result

            return bool(getattr(result, "success", False))

        return repair

    def _build_executor(
        self,
        executor: Callable | AgentExecutor | None,
    ) -> Callable:
        if executor is None:
            if self.manager.agent_executor is not None:
                return self.manager.agent_executor

            async def generated_project_executor(request: AgentRequest) -> AgentResult:
                """Complete the bookkeeping task for already-generated project files."""
                task = self.manager.task_engine.get(request.task_id)
                agent_name = task.assigned_agent or "factory-engineer"
                return AgentResult(
                    task_id=request.task_id,
                    agent_name=agent_name,
                    success=True,
                    output="Generated project files are ready for QA.",
                )

            return generated_project_executor

        if isinstance(executor, AgentExecutor):
            return self._agent_executor_adapter(executor)

        return executor

    def _agent_executor_adapter(
        self,
        executor: AgentExecutor,
    ) -> Callable:
        async def run(request: AgentRequest):
            task = self.manager.task_engine.get(request.task_id)
            agent_name = task.assigned_agent

            if agent_name is None:
                raise RuntimeError(
                    f"Task {request.task_id} has no assigned agent"
                )

            agent = self.manager.agent_registry.get(agent_name)

            if agent is None:
                raise RuntimeError(
                    f"Agent '{agent_name}' is not registered"
                )

            context = AgentExecutionContext(
                agent=agent,
                allowed_permissions=agent.permissions,
            )

            return await executor.execute(context, request)

        return run

    async def _execute_tasks(self, executor: Callable | None) -> None:
        while True:
            decision = await self.manager.tick(executor=executor)

            if decision.decision.value == "complete_mission":
                return

            if decision.decision.value == "wait":
                if decision.task_id is None:
                    raise RuntimeError(decision.reason)

                task = self.manager.task_engine.get(decision.task_id)

                if task.status.value == "failed":
                    raise RuntimeError(decision.reason)

                raise RuntimeError(decision.reason)

            if decision.task_id is None:
                raise RuntimeError("Manager started a task without a task ID")

    def _transition_to_development(self, project: Project) -> Project:
        for status in (
            ProjectStatus.RESEARCH,
            ProjectStatus.VALIDATION,
            ProjectStatus.PLANNING,
            ProjectStatus.ARCHITECTURE,
            ProjectStatus.DEVELOPMENT,
        ):
            project = self.project_engine.transition(project.id, status)

        return project

