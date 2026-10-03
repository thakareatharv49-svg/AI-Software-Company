from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

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
from src.qa.execution.runner import QARunner
from src.qa.models.contracts import QATestRequest, QATestResult
from src.qa.models.enums import QATestStatus
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
        reviewer: CodeReviewer | None = None,
        github: GitHubAutomation | None = None,
        memory: MemoryService | None = None,
    ) -> None:
        self.project_engine = project_engine or ProjectEngine()
        self.manager = manager or MasterManager()
        self.qa_runner = qa_runner or QARunner()
        self.reviewer = reviewer or CodeReviewer()
        self.github = github
        self.memory = memory or MemoryService()

    async def execute(
        self,
        *,
        project_request: ProjectCreateRequest,
        mission: Mission,
        tasks: Sequence[TaskPlanItem],
        qa_request: QATestRequest,
        files: dict[str, str],
        agent_executor: Callable | None = None,
        github_repository: GitHubRepository | None = None,
        pull_request_head: str | None = None,
    ) -> PipelineResult:
        project = self.project_engine.create(project_request)

        project = self._transition_to_development(project)

        mission = replace(mission, project_id=project.id)

        self.manager.start_mission(mission)
        task_ids = self.manager.create_plan(tasks)

        await self._execute_tasks(agent_executor)

        project = self.project_engine.transition(
            project.id,
            ProjectStatus.TESTING,
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

        self.project_engine.transition(
            project.id,
            ProjectStatus.REVIEW,
        )

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
                body=project.objective,
            )

            if not github_result.success:
                self.project_engine.block(project.id)
                raise RuntimeError(
                    f"GitHub release step failed: "
                    f"{github_result.message}"
                )

            github_message = github_result.message

        self.project_engine.transition(
            project.id,
            ProjectStatus.RELEASE,
        )

        project = self.project_engine.complete(project.id)

        memory_entry = self.memory.remember(
            MemoryCreateRequest(
                memory_type=MemoryType.PROJECT,
                title=f"Completed project: {project.name}",
                content=(
                    f"Project '{project.name}' completed successfully. "
                    f"Objective: {project.objective}. "
                    f"Tasks completed: {len(task_ids)}."
                ),
                project_id=project.id,
                tags=["project-completed", "pipeline"],
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

    def _transition_to_development(self, project: Project) -> Project:
        for status in (
            ProjectStatus.RESEARCH,
            ProjectStatus.VALIDATION,
            ProjectStatus.PLANNING,
            ProjectStatus.ARCHITECTURE,
            ProjectStatus.DEVELOPMENT,
        ):
            project = self.project_engine.transition(
                project.id,
                status,
            )

        return project

    async def _execute_tasks(
        self,
        executor: Callable | None,
    ) -> None:
        while True:
            decision = await self.manager.tick(
                executor=executor,
            )

            if decision.decision.value == "complete_mission":
                return

            if decision.decision.value == "wait":
                if decision.task_id is None:
                    raise RuntimeError(
                        f"Task execution blocked: {decision.reason}"
                    )

                task = self.manager.task_engine.get(
                    decision.task_id
                )

                if task.status.value == "failed":
                    raise RuntimeError(
                        f"Task failed: {task.error or decision.reason}"
                    )

                raise RuntimeError(
                    f"Task execution stopped: {decision.reason}"
                )

            if decision.task_id is None:
                raise RuntimeError(
                    f"Manager returned no task: {decision.reason}"
                )


