from collections.abc import Callable
import os
from dataclasses import dataclass, replace
from pathlib import Path

from src.agents.execution.context import AgentExecutionContext
from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentRequest, AgentResult
from src.company.gates.quality import ProductionQualityGate
from src.company.github_native.publish_queue import GitHubPublishQueue
from src.company.github_native.service import GitHubNativeService
from src.company.project_generator import GeneratedProject, OllamaProjectGenerator
from src.config.settings import settings
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
    github_pending: bool = False
    browser_preview: bool = False
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
        if github_native is not None:
            self.github_native = github_native
        elif self.github is not None:
            self.github_native = GitHubNativeService(github=self.github)
        else:
            self.github_native = configured_github_native
        self.github_publish_queue = GitHubPublishQueue()
        self.memory = memory or MemoryService()
        self.cross_project_memory = cross_project_memory or CrossProjectMemory()
        self.learning = learning or LearningEngine()
        self.project_generator = project_generator or OllamaProjectGenerator()
        self._active_generated_files: dict[str, str] = {}
        self.recovery = RecoveryService(max_attempts=3)
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
            repair_agent_executor or agent_executor,
            project_name=project_request.name,
            objective=project_request.objective,
            project_id=project.id,
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
            self.project_engine.transition(project.id, ProjectStatus.DEBUGGING)
            raise RuntimeError(
                f"QA failed for project {project.id}: {debug_result.final_error}"
            )
        qa_result = await self.qa_runner.run(qa_request)
        if qa_result.status != QATestStatus.PASSED:
            self.project_engine.transition(project.id, ProjectStatus.DEBUGGING)
            raise RuntimeError(
                f"QA failed for project {project.id}: "
                f"{qa_result.stderr or qa_result.stdout}"
            )
        # QA repair agents can edit the workspace on disk. Reconcile those
        # edits before security review and GitHub publishing so the delivered
        # files are exactly the version that passed the final QA command.
        self._sync_generated_files_from_workspace(
            qa_request.working_directory,
            files,
        )
        self.project_engine.transition(project.id, ProjectStatus.SECURITY)
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
            self.project_engine.transition(project.id, ProjectStatus.DEBUGGING)
            raise RuntimeError(
                f"Code review failed for project {project.id}: {review_result.summary}"
            )
        self.project_engine.transition(project.id, ProjectStatus.REVIEW)
        gate = self.quality_gate.evaluate(
            qa_passed=qa_result.status == QATestStatus.PASSED,
            security_approved=review_result.status.value == "approved",
            github_ready=(
                github_repository is None and pull_request_head is None
            ) or (
                self.github is not None
                and github_repository is not None
                and pull_request_head is not None
            ),
            deployment_ready=True,
        )
        self._publish_event(
            "production.gate.evaluated",
            project_id=project.id,
            payload={"approved": gate.approved, "reasons": gate.reasons},
        )
        if not gate.approved:
            raise RuntimeError("Production quality gate rejected the generated project")
        project = self.project_engine.transition(project.id, ProjectStatus.COMPLETED)
        return PipelineResult(
            project=project,
            task_ids=task_ids,
            qa_result=qa_result,
            review_result=review_result,
        )

    async def _execute_tasks(self, executor: Callable | None) -> None:
        while True:
            decision = await self.manager.tick_parallel(
                executor=executor,
                max_concurrency=settings.factory_max_parallel_tasks,
            )
            if decision.decision.value == "complete_mission":
                return
            if decision.decision.value == "wait":
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
