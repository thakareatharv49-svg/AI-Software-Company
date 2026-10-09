from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from src.company.autonomous_project import (
    AutonomousProjectRequest,
    AutonomousProjectResult,
    AutonomousProjectRunner,
)
from src.company.acceptance import AutonomousCompanyAcceptance
from src.company.mission_controller.models import MissionPlan
from src.company.models.contracts import CompanyMission
from src.company.workspace import ProjectExecutionService


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
                on_progress(plan)

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
        record_progress(
            "product_generation", "completed", "Mission-specific project files generated."
        )
        workspace = self.workspace_service.create_workspace(mission.id)

        try:
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
            request = replace(
                request,
                stage_callback=record_progress,
            )
            result = await self.runner.run(request)
            report = AutonomousCompanyAcceptance().evaluate(result)
            if not report.passed:
                failures = [
                    f"{check.name}: {check.detail}"
                    for check in report.checks
                    if not check.passed
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
    def _record_stage_progress(
        plan: MissionPlan,
        stage_name: str,
        status: str,
        detail: str,
    ) -> None:
        """Project autonomous lifecycle progress onto the visible factory plan."""
        normalized_status = str(status).strip().lower()
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
