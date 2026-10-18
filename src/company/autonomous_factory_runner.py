from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Protocol

from src.company.autonomous_project import (
    AutonomousProjectRequest,
    AutonomousProjectResult,
    AutonomousProjectRunner,
)
from src.company.acceptance import AutonomousCompanyAcceptance
from src.company.generated_task_planning import build_generated_task_plan
from src.company.mission_controller.models import MissionPlan
from src.company.models.contracts import CompanyMission
from src.company.workspace import ProjectExecutionService
from src.security.redaction import redact_sensitive_text


class AutonomousProjectRunnerProtocol(Protocol):
    async def run(self, request: AutonomousProjectRequest) -> AutonomousProjectResult: ...


AutonomousProjectRequestBuilder = Callable[
    [CompanyMission, MissionPlan],
    AutonomousProjectRequest | Awaitable[AutonomousProjectRequest],
]


class FactoryAutonomousRunner:
    """Adapter that connects a factory mission to the real M36 runner."""

    def __init__(
        self,
        runner: AutonomousProjectRunner,
        request_builder: AutonomousProjectRequestBuilder,
        workspace_service: ProjectExecutionService | None = None,
    ) -> None:
        self.runner = runner
        self.request_builder = request_builder
        self.workspace_service = workspace_service or ProjectExecutionService(
            Path(__file__).resolve().parents[2] / "generated-products"
        )

    async def run(
        self,
        mission: CompanyMission,
        plan: MissionPlan,
        on_progress: Callable[[MissionPlan], None] | None = None,
    ) -> AutonomousProjectResult:
        def record_progress(stage_name: str, status: str, detail: str) -> None:
            self._record_stage_progress(plan, stage_name, status, detail)
            if on_progress is not None:
                # Progress persistence is diagnostic telemetry. A storage outage
                # must not abort generation or the autonomous lifecycle itself.
                try:
                    on_progress(plan)
                except Exception:
                    pass

        record_progress(
            "product_generation", "running", "Generating mission-specific project files."
        )
        try:
            request = self.request_builder(mission, plan)
            if hasattr(request, "__await__"):
                request = await request
        except Exception as exc:
            record_progress(
                "product_generation", "failed",
                f"{type(exc).__name__}: {exc}",
            )
            raise
        for key, value in self._generation_metrics_updates(request).items():
            setattr(plan, key, value)
        if on_progress is not None:
            # Preserve generation usage even if workspace validation fails later.
            try:
                on_progress(plan)
            except Exception:
                pass

        try:
            self._validate_generated_files(request.files)
            # Generated files are the most concrete architecture artifact available
            # at this point. When the request builder supplies only a single broad
            # task, derive work packages from the actual output so frontend, backend,
            # and quality work are visible to the execution pipeline. Preserve an
            # explicitly decomposed task plan supplied by the caller.
            # Some legacy/test request builders intentionally return minimal
            # request-like objects. Only expand task plans when this request
            # contract actually exposes tasks; do not break workspace validation
            # for callers that have not adopted task planning yet.
            if hasattr(request, "tasks"):
                request = replace(
                    request,
                    tasks=self._derive_tasks_from_generated_files(request, mission),
                )
            workspace = self.workspace_service.create_workspace(mission.id)
            for path, content in request.files.items():
                workspace.write_file(path, content)

            if request.qa_request is not None:
                request = replace(
                    request,
                    qa_request=request.qa_request.model_copy(
                        update={
                            "working_directory": str(workspace.root),
                        }
                    ),
                )
        except Exception as exc:
            record_progress(
                "product_generation",
                "failed",
                f"Workspace preparation failed: {type(exc).__name__}: {exc}",
            )
            raise

        record_progress(
            "product_generation", "completed", "Mission-specific project files generated."
        )
        request = replace(request, stage_callback=record_progress)

        try:
            result = await self.runner.run(request)
        except Exception as exc:
            self._record_runner_failure(plan, exc)
            if on_progress is not None:
                # Preserve the failure diagnosis even when the runner exits
                # before emitting its own stage-progress callback.
                try:
                    on_progress(plan)
                except Exception:
                    pass
            raise

        for key, value in self._quality_evidence_updates(
            result,
            getattr(request.qa_request, 'command', []) if request.qa_request is not None else [],
        ).items():
            setattr(plan, key, value)
        if on_progress is not None:
            # Persist evidence from the exact successful pipeline run before the
            # mission can be marked completed or submitted for human review.
            try:
                on_progress(plan)
            except Exception:
                pass

        try:
            report = AutonomousCompanyAcceptance().evaluate(result)
            if not report.passed:
                failed_checks = [check for check in report.checks if not check.passed]
                self._record_acceptance_failures(plan, failed_checks)
                if on_progress is not None:
                    # Persist the actionable failure state before raising. This
                    # callback is best-effort just like ordinary stage telemetry.
                    try:
                        on_progress(plan)
                    except Exception:
                        pass
                failures = [
                    f"{check.name}: {check.detail}"
                    for check in failed_checks
                ]
                raise RuntimeError(
                    "Autonomous project failed final acceptance: "
                    + "; ".join(failures)
                )
            return result
        finally:
            # Completed workspaces are intentionally retained for the product
            # viewer. Failed attempts are also retained for diagnostics/retry.
            pass

    @staticmethod
    def _generation_metrics_updates(request) -> dict:
        """Copy bounded model usage metrics into the durable mission plan."""
        return {
            "generation_model_calls": max(0, int(getattr(request, "generation_model_calls", 0) or 0)),
            "generation_duration_ms": max(0, int(getattr(request, "generation_duration_ms", 0) or 0)),
            "generation_prompt_tokens": max(0, int(getattr(request, "generation_prompt_tokens", 0) or 0)),
            "generation_output_tokens": max(0, int(getattr(request, "generation_output_tokens", 0) or 0)),
        }

    @staticmethod
    def _quality_evidence_updates(result: AutonomousProjectResult, qa_command: list[str]) -> dict:
        """Build review evidence from actual runner results, never caller text."""
        qa = result.pipeline.qa_result
        security = result.pipeline.review_result
        qa_status = str(getattr(qa.status, "value", qa.status))
        security_status = str(getattr(security.status, "value", security.status))
        # Evidence should explain failures well enough to repair them, but never
        # expose secrets or retain unbounded subprocess output in mission history.
        command = [
            redact_sensitive_text(str(part))[:500]
            for part in qa_command
        ]
        qa_exit_code = getattr(qa, "exit_code", None)
        qa_duration_ms = getattr(qa, "duration_ms", None)
        security_approved = bool(getattr(security, "approved", security_status == "approved"))
        stdout = redact_sensitive_text(str(getattr(qa, "stdout", "") or ""))[:2000]
        stderr = redact_sensitive_text(str(getattr(qa, "stderr", "") or ""))[:2000]
        checks = getattr(result.pipeline, "qa_checks", []) or []
        check_evidence = "; ".join(
            f"{redact_sensitive_text(str(check.get('kind', 'check')))[:80]}:"
            f"{redact_sensitive_text(str(check.get('status', 'unknown')))[:40]} "
            f"exit={check.get('exit_code', 'unknown')} "
            f"duration_ms={check.get('duration_ms', 'unknown')} "
            f"command={' '.join(redact_sensitive_text(str(part))[:120] for part in check.get('command', []))[:300]}"
            for check in checks[:12]
            if isinstance(check, dict)
        )
        browser_check = getattr(result.pipeline, "browser_acceptance", None)
        if isinstance(browser_check, dict):
            browser_evidence = (
                f"browser_status={redact_sensitive_text(str(browser_check.get('status', 'unknown')))[:40]}; "
                f"routes={redact_sensitive_text(','.join(str(item) for item in browser_check.get('routes_checked', [])[:8]))[:500]}; "
                f"interactions={redact_sensitive_text(','.join(str(item) for item in browser_check.get('interactions_checked', [])[:8]))[:500]}; "
                f"detail={redact_sensitive_text(str(browser_check.get('detail', '')))[:1000]}"
            )
        else:
            browser_evidence = "browser_status=not_recorded"
        qa_evidence = (
            "Factory QA runner result: "
            f"status={qa_status}; exit_code={qa_exit_code}; "
            f"duration_ms={qa_duration_ms}; command={' '.join(command)[:500]}; "
            f"stdout={stdout or '[empty]'}; stderr={stderr or '[empty]'}; "
            f"checks={check_evidence or '[no per-command ledger available]'}; "
            f"{browser_evidence}"
        )[:5200]
        security_summary = redact_sensitive_text(
            str(getattr(security, "summary", "") or "")
        )[:1000]
        security_evidence = (
            "Factory security reviewer result: "
            f"status={security_status}; approved={security_approved}; "
            f"summary={security_summary or 'No summary supplied.'}"
        )
        return {
            "qa_status": qa_status,
            "qa_exit_code": qa_exit_code,
            "qa_duration_ms": qa_duration_ms,
            "qa_command": command,
            "qa_evidence": qa_evidence,
            "security_status": security_status,
            "security_summary": security_summary,
            "security_evidence": security_evidence,
        }

    @staticmethod
    def _derive_tasks_from_generated_files(request, mission):
        """Expand a single broad task when generated output spans subsystems."""
        existing_tasks = getattr(request, "tasks", ())
        if len(existing_tasks) > 1:
            return existing_tasks
        project_request = getattr(request, "project_request", None)
        # Older adapters may not provide the structured project request that
        # generated planning needs. Preserve their original task behavior.
        if project_request is None:
            return existing_tasks
        project_name = getattr(project_request, "name", None) or mission.name
        project_objective = (
            getattr(project_request, "objective", None) or mission.objective
        )
        generated_plan = build_generated_task_plan(
            project_name,
            project_objective,
            request.files,
        )
        implementation_packages = sum(
            1 for task in generated_plan
            if not task.title.startswith("Validate ")
        )
        if not request.tasks or implementation_packages > 1:
            return generated_plan
        return existing_tasks

    @staticmethod
    def _validate_generated_files(files: dict[str, str]) -> None:
        """Reject empty or unsafe artifact plans before touching the workspace."""
        if not isinstance(files, dict) or not files:
            raise ValueError("Generated project contains no files")

        has_content = False
        for raw_path, content in files.items():
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError("Generated project contains an empty file path")
            if not isinstance(content, str):
                raise ValueError(f"Generated file {raw_path!r} has non-text content")

            # Normalize Windows separators too, even when the factory runs on POSIX.
            normalized = raw_path.replace("\\", "/")
            path = PurePosixPath(normalized)
            if (
                path.is_absolute()
                or any(part in {"", ".", ".."} for part in path.parts)
                or (path.parts and path.parts[0].endswith(":"))
                or "\x00" in normalized
            ):
                raise ValueError(f"Generated project contains unsafe path: {raw_path!r}")
            has_content = has_content or bool(content.strip())

        if not has_content:
            raise ValueError("Generated project files are all empty")

    @staticmethod
    def _record_runner_failure(plan: MissionPlan, error: Exception) -> None:
        """Ensure an unexpected runner exception is visible in the mission plan."""
        steps = {step.stage.value: step for step in plan.steps}
        if any(step.status == "failed" for step in plan.steps):
            return

        message = redact_sensitive_text(
            f"{type(error).__name__}: {error}"
        )[:4000]
        stage_name = None
        prefix = "Autonomous stage '"
        if prefix in str(error):
            stage_name = str(error).split(prefix, 1)[1].split("'", 1)[0]

        stage_aliases = {
            "ai_ceo": "product",
            "research_handoff": "research",
            "product_definition": "product",
            "engineering_qa_security_github": "execution",
        }
        target = steps.get(stage_aliases.get(stage_name, stage_name or ""))
        if target is None:
            target = next(
                (step for step in plan.steps if step.status == "running"),
                steps.get("execution"),
            )
        if target is not None:
            target.status = "failed"
            target.detail = f"Autonomous runner failed: {message}"

    @staticmethod
    def _record_acceptance_failures(plan: MissionPlan, failed_checks) -> None:
        """Mark the precise factory stages rejected by final acceptance."""
        check_to_stage = {
            "mission_approved": "product",
            "ai_ceo": "product",
            "research": "research",
            "research_handoff": "research",
            "product_definition": "product",
            "architecture": "architecture",
            "engineering_qa_security_github": "execution",
            "real_project": "execution",
            "qa_passed": "qa",
            "security_approved": "security",
            "deployment_completed": "deployment",
            "monitoring_completed": "monitoring",
            "learning_recorded": "learning",
        }
        steps = {step.stage.value: step for step in plan.steps}
        for check in failed_checks:
            stage_name = check_to_stage.get(check.name, "execution")
            step = steps.get(stage_name)
            if step is None:
                continue
            step.status = "failed"
            step.detail = (
                f"Final acceptance failed ({check.name}): {check.detail}"
            )

    @staticmethod
    def _record_stage_progress(
        plan: MissionPlan,
        stage_name: str,
        status: str,
        detail: str,
    ) -> None:
        """Project autonomous lifecycle progress onto the visible factory plan."""
        normalized_status = str(status).strip().lower()
        # Stage details are persisted in mission history and can surface in the
        # HQ UI. Sanitize and bound them even when an upstream stage fails before
        # the normal QA evidence path runs.
        detail = redact_sensitive_text(str(detail))[:4000]
        mappings: dict[str, tuple[str, ...]] = {
            "product_generation": ("execution",),
            "ai_ceo": ("product",),
            "research": ("research",),
            "research_handoff": ("research",),
            "product_definition": ("product",),
            "architecture": ("architecture",),
            "engineering_qa_security_github": (
                "tasks", "agents", "execution", "qa", "security", "github"
            ),
            "deployment": ("deployment",),
            "monitoring": ("monitoring",),
            "learning": ("learning",),
        }
        target_names = mappings.get(stage_name, ())
        if not target_names:
            return

        step_by_name = {step.stage.value: step for step in plan.steps}
        failure_text = detail.casefold()
        if stage_name == "engineering_qa_security_github":
            if normalized_status == "running":
                target_names = ("tasks", "agents", "execution")
            elif normalized_status == "failed":
                if "qa failed" in failure_text or (
                    "test" in failure_text and "failed" in failure_text
                ):
                    for name in ("tasks", "agents", "execution"):
                        step = step_by_name.get(name)
                        if step is not None:
                            step.status = "completed"
                            step.detail = "Engineering completed before QA failed."
                    target_names = ("qa",)
                elif "code review failed" in failure_text or "security" in failure_text:
                    for name in ("tasks", "agents", "execution", "qa"):
                        step = step_by_name.get(name)
                        if step is not None:
                            step.status = "completed"
                            step.detail = "Stage completed before security review failed."
                    target_names = ("security",)
                else:
                    for name in ("tasks", "agents"):
                        step = step_by_name.get(name)
                        if step is not None:
                            step.status = "completed"
                            step.detail = "Engineering setup completed."
                    target_names = ("execution",)
        targets = [step_by_name[name] for name in target_names if name in step_by_name]

        for step in targets:
            if normalized_status == "running" and step.status not in {"running", "completed"}:
                step.attempts += 1
            step.status = normalized_status
            step.detail = detail
