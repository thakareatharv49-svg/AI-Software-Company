from collections.abc import Callable
from dataclasses import dataclass, replace

from src.agents.execution.context import AgentExecutionContext
from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentRequest
from src.github.automation.automation import GitHubAutomation
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
        memory: MemoryService | None = None,
    ) -> None:
        self.project_engine = project_engine or ProjectEngine()
        self.manager = manager or MasterManager()
        self.qa_runner = qa_runner or QARunner()
        self.debugger = debugger or AutonomousDebugger(
            qa_runner=self.qa_runner,
        )
        self.reviewer = reviewer or CodeReviewer()
        self.github = github
        self.memory = memory or MemoryService()

    async def execute(
        self,
        *,
        project_request: ProjectCreateRequest,
        mission: Mission,
        tasks: list[TaskPlanItem],
        qa_request: QATestRequest,
        files: dict[str, str],
        agent_executor: Callable | AgentExecutor | None = None,
        github_repository: GitHubRepository | None = None,
        pull_request_head: str | None = None,
    ) -> PipelineResult:
        project = self.project_engine.create(project_request)
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

        debug_result = await self.debugger.run(qa_request)

        if debug_result.status == DebugStatus.BLOCKED:
            self.project_engine.transition(
                project.id,
                ProjectStatus.DEBUGGING,
            )
            raise RuntimeError(
                f"QA debugging failed for project {project.id}: "
                f"{debug_result.final_error}"
            )

        qa_result = await self.qa_runner.run(qa_request)

        if qa_result.status != QATestStatus.PASSED:
            self.project_engine.transition(
                project.id,
                ProjectStatus.DEBUGGING,
            )
            raise RuntimeError(
                f"QA verification failed for project {project.id}: "
                f"{qa_result.stderr or qa_result.stdout}"
            )

        self.project_engine.transition(
            project.id,
            ProjectStatus.SECURITY,
        )

        review_result = self.reviewer.review(
            CodeReviewRequest(
                files=files,
                summary=f"Automated review for project {project.name}",
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

        github_message = None

        if (
            self.github is not None
            and github_repository is not None
            and pull_request_head is not None
        ):
            github_result = await self.github.open_pull_request(
                github_repository,
                title=f"feat: complete {project.name}",
                head=pull_request_head,
                body=project.description,
            )

            if not github_result.success:
                self.project_engine.transition(
                    project.id,
                    ProjectStatus.BLOCKED,
                )
                raise RuntimeError(github_result.message)

            github_message = github_result.message

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

        return PipelineResult(
            project=project,
            task_ids=task_ids,
            qa_result=qa_result,
            review_result=review_result,
            github_message=github_message,
            memory_id=memory_entry.id,
        )

    def _build_executor(
        self,
        executor: Callable | AgentExecutor | None,
    ) -> Callable:
        if executor is None:
            return self.manager.agent_executor

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

