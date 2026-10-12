from collections.abc import Callable
import os
from dataclasses import dataclass, replace
from pathlib import Path

from src.agents.execution.context import AgentExecutionContext
from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentRequest, AgentResult
from src.company.artifact_validation import validate_generated_artifacts
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
        self._active_project_id: str | None = None

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
        resume_project_id: str | None = None,
    ) -> PipelineResult:
        self._active_generated_files = files
        if resume_project_id is None:
            project = self.project_engine.create(project_request)
            self._active_project_id = project.id
        else:
            project = self.project_engine.get(resume_project_id)
            self._active_project_id = project.id
            if project.status == ProjectStatus.BLOCKED:
                project = self.project_engine.transition(
                    project.id, ProjectStatus.DEVELOPMENT
                )
            elif project.status in {ProjectStatus.SECURITY, ProjectStatus.REVIEW}:
                project = self.project_engine.transition(
                    project.id, ProjectStatus.DEBUGGING
                )

        self._publish_event(
            "project.execution.started",
            project_id=project.id,
            payload={
                "project_name": project.name,
                "objective": project.objective,
            },
        )
        if resume_project_id is None:
            project = self._transition_to_development(project)
        mission = replace(mission, project_id=project.id)

        self.manager.start_mission(mission)
        existing_tasks = self.manager.task_engine.list(project_id=project.id)
        plan_matches_existing = (
            len(existing_tasks) == len(tasks)
            and all(
                existing.title == planned.title.strip()
                and existing.description == planned.description
                for existing, planned in zip(existing_tasks, tasks, strict=True)
            )
        )
        if existing_tasks and plan_matches_existing:
            task_ids = [task.id for task in existing_tasks]
            # Retry failed or interrupted tasks in place, retaining completed
            # dependencies and task history instead of duplicating the plan.
            for task in existing_tasks:
                if task.status.value == "in_progress":
                    self.manager.task_engine.fail(
                        task.id,
                        "Interrupted by a prior pipeline attempt",
                    )
                current = self.manager.task_engine.get(task.id)
                if current.status.value == "failed":
                    self.manager.task_engine.retry(task.id)
        else:
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
            self.project_engine.transition(
                project.id,
                ProjectStatus.DEBUGGING,
            )
            raise RuntimeError(
                f"QA failed for project {project.id}: "
                f"{debug_result.final_error}"
            )

        # The debugger already ran the successful command (including after any
        # repair). Reuse that exact result instead of paying for a duplicate run.
        qa_result = debug_result.test_result or await self.qa_runner.run(qa_request)

        if qa_result.status != QATestStatus.PASSED:
            self.project_engine.transition(
                project.id,
                ProjectStatus.DEBUGGING,
            )
            raise RuntimeError(
                f"QA failed for project {project.id}: "
                f"{qa_result.stderr or qa_result.stdout}"
            )

        # A custom smoke/build command must not silently replace the generated
        # product's own test suite. If tests are present and the configured QA
        # command did not already invoke pytest, run the suite separately in the
        # isolated project workspace before security review or delivery.
        has_product_tests = self._has_generated_python_tests(files)
        configured_command = [part.casefold() for part in qa_request.command]
        runs_pytest = any(
            part == "pytest" or part.endswith("/pytest") or part.endswith("\\\\pytest.exe")
            for part in configured_command
        ) or any(
            configured_command[index:index + 2] == ["-m", "pytest"]
            for index in range(max(0, len(configured_command) - 1))
        )
        if has_product_tests and not runs_pytest:
            product_test_request = qa_request.model_copy(
                update={
                    "command": ["python", "-m", "pytest", "-q"],
                }
            )
            product_test_debug = await self.debugger.run(
                product_test_request,
                repair=repair_callback,
            )
            if product_test_debug.status == DebugStatus.BLOCKED:
                self.project_engine.transition(
                    project.id,
                    ProjectStatus.DEBUGGING,
                )
                self._publish_event(
                    "qa.generated_product_tests.repair_blocked",
                    project_id=project.id,
                    payload={
                        "framework": "pytest",
                        "attempts": len(product_test_debug.attempts),
                        "error": product_test_debug.final_error,
                    },
                )
                raise RuntimeError(
                    f"Generated product tests failed for project {project.id}: "
                    f"{product_test_debug.final_error}"
                )
            # The debugger's successful final attempt is already the verification
            # of the post-repair workspace; do not execute the suite a second time.
            product_test_result = product_test_debug.test_result or await self.qa_runner.run(product_test_request)
            self._publish_event(
                "qa.generated_product_tests.completed",
                project_id=project.id,
                payload={
                    "framework": "pytest",
                    "status": product_test_result.status.value,
                    "exit_code": product_test_result.exit_code,
                    "duration_ms": product_test_result.duration_ms,
                    "repair_attempts": len(product_test_debug.attempts),
                },
            )
            if product_test_result.status != QATestStatus.PASSED:
                self.project_engine.transition(
                    project.id,
                    ProjectStatus.DEBUGGING,
                )
                raise RuntimeError(
                    f"Generated product tests failed for project {project.id}: "
                    f"{product_test_result.stderr or product_test_result.stdout}"
                )

        # Browser products can ship executable Node test suites as well as
        # Python tests. Run conventional Node test files independently unless the
        # configured QA command already invokes Node's built-in test runner.
        javascript_test_paths = self._generated_javascript_test_paths(files)
        has_javascript_tests = bool(javascript_test_paths)
        runs_node_tests = any(
            part == "--test" and index > 0
            and configured_command[index - 1] in {"node", "node.exe"}
            for index, part in enumerate(configured_command)
        )
        has_non_default_node_test_names = any(
            ".spec." in path.casefold() for path in javascript_test_paths
        )
        if has_javascript_tests and (
            not runs_node_tests or has_non_default_node_test_names
        ):
            # Explicit paths ensure .spec.* suites run too; Node's default
            # discovery patterns do not include every naming convention.
            javascript_test_request = qa_request.model_copy(
                update={"command": ["node", "--test", *javascript_test_paths]}
            )
            javascript_test_debug = await self.debugger.run(
                javascript_test_request,
                repair=repair_callback,
            )
            if javascript_test_debug.status == DebugStatus.BLOCKED:
                self.project_engine.transition(
                    project.id,
                    ProjectStatus.DEBUGGING,
                )
                self._publish_event(
                    "qa.generated_product_tests.repair_blocked",
                    project_id=project.id,
                    payload={
                        "framework": "node:test",
                        "attempts": len(javascript_test_debug.attempts),
                        "error": javascript_test_debug.final_error,
                    },
                )
                raise RuntimeError(
                    f"Generated JavaScript product tests failed for project {project.id}: "
                    f"{javascript_test_debug.final_error}"
                )
            # Reuse the debugger's successful final attempt to avoid a duplicate
            # Node process after the suite has already passed.
            javascript_test_result = javascript_test_debug.test_result or await self.qa_runner.run(javascript_test_request)
            self._publish_event(
                "qa.generated_product_tests.completed",
                project_id=project.id,
                payload={
                    "framework": "node:test",
                    "status": javascript_test_result.status.value,
                    "exit_code": javascript_test_result.exit_code,
                    "duration_ms": javascript_test_result.duration_ms,
                    "repair_attempts": len(javascript_test_debug.attempts),
                },
            )
            if javascript_test_result.status != QATestStatus.PASSED:
                self.project_engine.transition(
                    project.id,
                    ProjectStatus.DEBUGGING,
                )
                raise RuntimeError(
                    f"Generated JavaScript product tests failed for project {project.id}: "
                    f"{javascript_test_result.stderr or javascript_test_result.stdout}"
                )

        # QA repair agents can edit the workspace on disk. Reconcile those
        # edits before security review and GitHub publishing so the delivered
        # files are exactly the version that passed the final QA command.
        self._sync_generated_files_from_workspace(
            qa_request.working_directory,
            files,
        )

        # Reject structurally broken deliverables before spending time on
        # security review. The workspace has already been reconciled after QA,
        # so this validates the exact files that would be reviewed and shipped.
        artifact_issues = validate_generated_artifacts(files)
        if artifact_issues:
            self.project_engine.transition(project.id, ProjectStatus.BLOCKED)
            self._publish_event(
                "production.artifacts.rejected",
                project_id=project.id,
                payload={"artifact_issues": artifact_issues},
            )
            raise RuntimeError(
                "Generated artifacts failed validation: " + " ".join(artifact_issues)
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
            # Local execution must remain valid even when GitHub publishing
            # is configured globally. GitHub readiness is required only when
            # this run explicitly requests repository/PR publication.
            github_ready=(
                github_repository is None
                and pull_request_head is None
            ) or (
                self.github is not None
                and github_repository is not None
                and pull_request_head is not None
            ),
            deployment_ready=True,
            artifacts_ready=not artifact_issues,
        )
        self._publish_event(
            "production.gate.evaluated",
            project_id=project.id,
            payload={
                "allowed": gate.allowed,
                "checks": gate.checks,
                "artifact_issues": artifact_issues,
            },
        )
        if not gate.allowed:
            self.project_engine.transition(project.id, ProjectStatus.BLOCKED)
            detail = " ".join(artifact_issues)
            raise RuntimeError(f"{gate.reason} {detail}".strip())

        github_message = None
        github_pending = False

        if (
            self.github is not None
            and github_repository is not None
            and pull_request_head is not None
            and self.github_native is not None
        ):
            publish_commit_message = f"feat: complete {project.name}"
            publish_error = None
            try:
                publish_result = await self.github_native.publish_files(
                    github_repository,
                    pull_request_head,
                    files,
                    publish_commit_message,
                )
                if publish_result.success:
                    github_message = (
                        "Published generated project directly to "
                        f"{github_repository.owner}/{github_repository.name}:"
                        f"{pull_request_head}"
                    )
                    for entry in self.github_publish_queue.due():
                        if (
                            entry.get("owner") == github_repository.owner
                            and entry.get("name") == github_repository.name
                            and entry.get("branch") == pull_request_head
                        ):
                            self.github_publish_queue.remove(entry)
                else:
                    publish_error = publish_result.message
            except Exception as exc:
                # Publishing is a delivery side-effect, not a build/QA gate.
                # Network errors and API failures must not discard a valid local product.
                publish_error = str(exc)

            if publish_error is not None:
                self.github_publish_queue.enqueue(
                    owner=github_repository.owner,
                    name=github_repository.name,
                    branch=pull_request_head,
                    files=dict(files),
                    message=publish_commit_message,
                )
                github_pending = True
                if self._is_github_rate_limited(publish_error):
                    github_message = (
                        "GitHub publishing is rate-limited. The local product "
                        "passed QA/security and is completed; publishing is queued."
                    )
                else:
                    github_message = (
                        "The local product passed QA/security and is completed, "
                        "but GitHub publishing failed and is queued for retry: "
                        f"{publish_error}"
                    )
                self._publish_event(
                    "github.publish.deferred",
                    project_id=project.id,
                    payload={
                        "repository": (
                            f"{github_repository.owner}/"
                            f"{github_repository.name}"
                        ),
                        "branch": pull_request_head,
                        "reason": publish_error,
                    },
                )

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
            github_pending=github_pending,
            browser_preview=("index.html" in files),
            memory_id=memory_entry.id,
        )

    @staticmethod
    def _is_github_rate_limited(message: str) -> bool:
        lowered = message.lower()
        return any(
            marker in lowered
            for marker in (
                "secondary rate limit",
                "temporarily blocked from content creation",
                "rate limit exceeded",
                "api rate limit",
                "github api 403",
            )
        )

    async def _flush_one_pending_github_publish(self) -> None:
        """Retry at most one due publish without blocking local project execution."""
        if self.github_native is None:
            return
        for entry in self.github_publish_queue.due()[:1]:
            repository = GitHubRepository(
                owner=str(entry.get("owner", "")),
                name=str(entry.get("name", "")),
            )
            branch = str(entry.get("branch", "main"))
            files = entry.get("files", {})
            if not repository.owner or not repository.name or not isinstance(files, dict):
                self.github_publish_queue.remove(entry)
                continue
            result = await self.github_native.publish_files(
                repository,
                branch,
                {str(path): str(content) for path, content in files.items()},
                str(entry.get("message", "feat: publish generated project")),
            )
            if result.success:
                self.github_publish_queue.remove(entry)
            elif self._is_github_rate_limited(result.message):
                self.github_publish_queue.enqueue(
                    owner=repository.owner,
                    name=repository.name,
                    branch=branch,
                    files={str(path): str(content) for path, content in files.items()},
                    message=str(entry.get("message", "feat: publish generated project")),
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
        self._active_project_id = None
        resume_project_id: str | None = None

        # Publishing is deliberately decoupled from project generation. A due
        # GitHub publish is retried once per factory run; a rate limit never
        # blocks the new project's local completion.
        try:
            await self._flush_one_pending_github_publish()
        except Exception:
            pass

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
                    resume_project_id=resume_project_id,
                )

                self.recovery.reset(project_id=result.project.id)
                self._active_project_id = None

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
                # Preserve source files created or repaired during this attempt
                # before deciding whether to retry. A retry must not silently
                # discard progress made in the shared project workspace.
                if self._active_project_id is not None:
                    resume_project_id = self._active_project_id
                self._preserve_workspace_progress(
                    qa_request.working_directory,
                    files,
                    attempt=self.recovery.attempts(
                        project_id=self._active_project_id,
                        stage=self._classify_recovery_stage(exc),
                    ) + 1,
                )
                recovery = self.recovery.record_failure(
                    error=exc,
                    project_id=self._active_project_id,
                    stage=self._classify_recovery_stage(exc),
                )

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
                        "stage": recovery.stage,
                        "error_type": recovery.error_type,
                        "error_message": recovery.error_message,
                        "repeated_failure": recovery.repeated_failure,
                    },
                )

                if not recovery.retryable:
                    self.recovery.reset(project_id=self._active_project_id)
                    raise

                self._publish_event(
                    "autonomous.run.recovery_available",
                    project_id=recovery.project_id,
                    payload={
                        "action": recovery.action,
                        "attempt": recovery.attempt,
                        "error_type": recovery.error_type,
                        "error_message": recovery.error_message,
                        "repeated_failure": recovery.repeated_failure
                    },
                )

    def _preserve_workspace_progress(
        self,
        working_directory: str,
        files: dict[str, str],
        *,
        attempt: int,
    ) -> None:
        """Merge recoverable workspace changes into the in-memory deliverable map."""
        workspace_files: dict[str, str] = {}
        try:
            self._sync_generated_files_from_workspace(
                working_directory,
                workspace_files,
            )
        except (OSError, RuntimeError) as exc:
            self._publish_event(
                "autonomous.run.progress_preservation_failed",
                payload={
                    "attempt": attempt,
                    "reason": str(exc)[:1000],
                },
            )
            return

        if not workspace_files:
            return

        changed_paths = [
            path for path, content in workspace_files.items()
            if files.get(path) != content
        ]
        if not changed_paths:
            return

        # Merge rather than replace: some generators keep initial artifacts in
        # memory before they have materialized every file in the workspace.
        # Existing workspace versions win, and newly created files are retained.
        files.update(workspace_files)
        self._publish_event(
            "autonomous.run.progress_preserved",
            payload={
                "attempt": attempt,
                "file_count": len(workspace_files),
                "changed_file_count": len(changed_paths),
                "changed_paths": sorted(changed_paths)[:100],
            },
        )

    @staticmethod
    def _has_generated_python_tests(files: dict[str, str]) -> bool:
        """Detect pytest-discoverable suites outside the conventional tests/ folder too."""
        for path in files:
            normalized = path.replace("\\", "/").lstrip("./").casefold()
            filename = normalized.rsplit("/", 1)[-1]
            if not normalized.endswith(".py"):
                continue
            if filename.startswith("test_") or filename.endswith("_test.py"):
                return True
        return False

    @staticmethod
    def _generated_javascript_test_paths(files: dict[str, str]) -> list[str]:
        """Return generated Node test files that should be executed explicitly."""
        suffixes = (
            ".test.js",
            ".spec.js",
            ".test.cjs",
            ".spec.cjs",
            ".test.mjs",
            ".spec.mjs",
        )
        return sorted(
            path.replace("\\", "/")
            for path in files
            if path.replace("\\", "/").casefold().endswith(suffixes)
        )

    @staticmethod
    def _has_generated_javascript_tests(files: dict[str, str]) -> bool:
        """Detect Node test suites regardless of directory or module format."""
        return bool(CompanyExecutionPipeline._generated_javascript_test_paths(files))

    @staticmethod
    def _classify_recovery_stage(error: Exception) -> str:
        """Map common pipeline errors to a stable recovery stage."""
        message = str(error).casefold()
        if "qa failed" in message or "product tests failed" in message:
            return "qa"
        if "code review failed" in message or "security" in message:
            return "security"
        if "artifact" in message or "browser preview" in message:
            return "artifacts"
        if "github" in message or "pull request" in message or "rate limit" in message:
            return "github"
        return "execution"

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

    @staticmethod
    def _sync_generated_files_from_workspace(
        working_directory: str,
        files: dict[str, str],
    ) -> None:
        """Refresh the deliverable file map from the post-repair workspace."""
        root = Path(working_directory).resolve()
        ignored_directories = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".factory-checkpoints",
            "dist",
            "build",
        }
        refreshed: dict[str, str] = {}
        file_count = 0
        total_bytes = 0
        max_file_bytes = 2_000_000
        max_total_bytes = 20_000_000
        max_files = 500

        if not root.is_dir():
            raise RuntimeError(
                f"Cannot synchronize generated files: workspace does not exist: {root}"
            )

        for current_root, directories, filenames in os.walk(root, topdown=True, followlinks=False):
            current = Path(current_root)
            directories[:] = sorted(
                name
                for name in directories
                if name not in ignored_directories
                and not (current / name).is_symlink()
            )
            for filename in sorted(filenames):
                path = current / filename
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    relative = path.relative_to(root)
                    resolved = path.resolve()
                    resolved.relative_to(root)
                    size = path.stat().st_size
                except (OSError, ValueError):
                    continue
                if size > max_file_bytes:
                    # Do not publish oversized or potentially binary artifacts.
                    continue
                if file_count >= max_files or total_bytes + size > max_total_bytes:
                    break
                try:
                    file_content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    continue

                refreshed[relative.as_posix()] = file_content
                file_count += 1
                total_bytes += size
            if file_count >= max_files or total_bytes >= max_total_bytes:
                break

        # Some pipeline callers and legacy integrations keep generated files only
        # in memory instead of materializing them in the QA workspace. In that case,
        # preserve the original deliverable rather than failing before security review.
        # When the workspace does contain readable files, it remains authoritative:
        # this synchronizes repairs and additions while removing stale/deleted files.
        if not refreshed:
            return
        files.clear()
        files.update(refreshed)

    def _build_repair_callback(
        self,
        executor: Callable | AgentExecutor | None,
        *,
        project_name: str,
        objective: str,
        project_id: str,
    ) -> Callable | None:
        def validate_repaired_files() -> bool:
            try:
                OllamaProjectGenerator._validate_repaired_output(
                    project_name,
                    objective,
                    GeneratedProject(
                        files=dict(self._active_generated_files),
                        test_command=["python", "-m", "pytest", "-q"],
                    ),
                )
            except RuntimeError as exc:
                self._publish_event(
                    "qa.repair.rejected",
                    project_id=project_id,
                    payload={"reason": str(exc)[:2000], "project_name": project_name},
                )
                return False
            return True

        if executor is None:
            async def generated_project_repair(request: QATestRequest, diagnosis) -> bool:
                repaired = await self.project_generator.repair(
                    files=self._active_generated_files,
                    failure=diagnosis.error,
                )
                # Validate repaired source before allowing another QA attempt to
                # pass with broken assets, invalid syntax, or weakened tests.
                try:
                    OllamaProjectGenerator._validate_repaired_output(
                        project_name, objective, repaired
                    )
                except RuntimeError as exc:
                    self._publish_event(
                        "qa.repair.rejected",
                        project_id=project_id,
                        payload={"reason": str(exc)[:2000], "project_name": project_name},
                    )
                    return False

                root = Path(request.working_directory).resolve()
                for relative_path, content in repaired.files.items():
                    target = (root / relative_path).resolve()
                    if target != root and root not in target.parents:
                        self._publish_event(
                            "qa.repair.rejected",
                            project_id=project_id,
                            payload={
                                "reason": f"Repair returned unsafe path: {relative_path!r}",
                                "project_name": project_name,
                            },
                        )
                        return False
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                self._active_generated_files.clear()
                self._active_generated_files.update(repaired.files)
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
                        "run the relevant test or command to verify the fix. "
                        "Do not remove or weaken behavioral tests."
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
                success = result.success
            elif isinstance(result, bool):
                success = result
            else:
                success = bool(getattr(result, "success", False))

            if not success:
                return False
            self._sync_generated_files_from_workspace(
                request.working_directory,
                self._active_generated_files,
            )
            return validate_repaired_files()

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

