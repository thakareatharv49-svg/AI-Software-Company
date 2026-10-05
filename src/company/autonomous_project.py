from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from inspect import isawaitable
from typing import Any

from company.ceo.ceo import AICEO
from company.ceo.models import CEOResult, Mission
from company.collaboration.bus import CollaborationBus, Handoff
from company.dashboard.service import CompanyDashboard, DashboardSnapshot
from company.execution.pipeline import CompanyExecutionPipeline, PipelineResult
from company.learning.engine import LearningEngine, LearningReport
from company.research.engine import ResearchEngine, ResearchProvider, ResearchReport
from src.github.models.contracts import GitHubRepository
from src.manager.models.contracts import Mission as ManagerMission
from src.manager.models.contracts import TaskPlanItem
from src.projects.models.contracts import ProjectCreateRequest
from src.qa.models.contracts import QATestRequest


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class StageResult:
    name: str
    status: StageStatus
    detail: str


DeploymentHook = Callable[[PipelineResult], str | Awaitable[str]]
MonitoringHook = Callable[[PipelineResult], str | Awaitable[str]]


@dataclass(frozen=True)
class AutonomousProjectRequest:
    mission: Mission
    research_query: str
    project_request: ProjectCreateRequest
    manager_mission: ManagerMission
    tasks: tuple[TaskPlanItem, ...]
    qa_request: QATestRequest
    files: dict[str, str]
    agent_executor: Callable[..., Any] | None = None
    repair_agent_executor: Callable[..., Any] | None = None
    github_repository: GitHubRepository | None = None
    pull_request_head: str | None = None


@dataclass(frozen=True)
class AutonomousProjectResult:
    ceo: CEOResult
    research: ResearchReport
    handoff: Handoff
    product_definition: dict[str, Any]
    architecture: dict[str, Any]
    pipeline: PipelineResult
    deployment: StageResult
    monitoring: StageResult
    learning: LearningReport
    dashboard: DashboardSnapshot
    stages: tuple[StageResult, ...]


class AutonomousProjectRunner:
    """Runs one bounded mission through the company's complete project lifecycle."""

    def __init__(
        self,
        *,
        research_provider: ResearchProvider,
        pipeline: CompanyExecutionPipeline | None = None,
        deployment: DeploymentHook | None = None,
        monitoring: MonitoringHook | None = None,
    ) -> None:
        self._ceo = AICEO()
        self._research = ResearchEngine(research_provider)
        self._collaboration = CollaborationBus()
        self._pipeline = pipeline or CompanyExecutionPipeline()
        self._deployment = deployment
        self._monitoring = monitoring
        self._learning = LearningEngine()

    async def run(self, request: AutonomousProjectRequest) -> AutonomousProjectResult:
        stages: list[StageResult] = []

        ceo = self._run_stage(
            stages,
            "ai_ceo",
            lambda: self._ceo.evaluate(request.mission),
        )
        if ceo.decision.requires_human or ceo.mission.status.value != "approved":
            raise RuntimeError(
                f"Mission was not approved: {ceo.decision.reason}"
            )

        research = self._run_stage(
            stages,
            "research",
            lambda: self._research.research(request.research_query),
        )

        handoff = self._run_stage(
            stages,
            "research_handoff",
            lambda: self._handoff(request.mission.mission_id, research),
        )

        product_definition = self._run_stage(
            stages,
            "product_definition",
            lambda: self._define_product(ceo, research),
        )

        architecture = self._run_stage(
            stages,
            "architecture",
            lambda: self._define_architecture(ceo, request),
        )

        pipeline_result = await self._run_async_stage(
            stages,
            "engineering_qa_security_github",
            lambda: self._pipeline.run_end_to_end(
                project_request=request.project_request,
                mission=request.manager_mission,
                tasks=list(request.tasks),
                qa_request=request.qa_request,
                files=request.files,
                agent_executor=request.agent_executor,
                repair_agent_executor=request.repair_agent_executor,
                github_repository=request.github_repository,
                pull_request_head=request.pull_request_head,
            ),
        )

        deployment = await self._delivery_stage(
            stages,
            "deployment",
            self._deployment,
            pipeline_result,
        )
        monitoring = await self._delivery_stage(
            stages,
            "monitoring",
            self._monitoring,
            pipeline_result,
        )

        learning = self._run_stage(
            stages,
            "learning",
            lambda: self._learning.analyze_executions(
                [
                    {
                        "success": True,
                        "actor": "autonomous-project-runner",
                        "run_id": pipeline_result.project.id,
                        "rounds": len(request.tasks),
                        "tool_calls": 0,
                    }
                ]
            ),
        )

        dashboard = self._build_dashboard(
            request=request,
            ceo=ceo,
            research=research,
            pipeline=pipeline_result,
            deployment=deployment,
            monitoring=monitoring,
            learning=learning,
        )
        stages.append(
            StageResult(
                "dashboard",
                StageStatus.COMPLETED,
                "Company state snapshot generated from the autonomous run.",
            )
        )

        return AutonomousProjectResult(
            ceo=ceo,
            research=research,
            handoff=handoff,
            product_definition=product_definition,
            architecture=architecture,
            pipeline=pipeline_result,
            deployment=deployment,
            monitoring=monitoring,
            learning=learning,
            dashboard=dashboard,
            stages=tuple(stages),
        )

    def _handoff(self, task_id: str, report: ResearchReport) -> Handoff:
        handoff = Handoff(
            task_id=task_id,
            sender="researcher",
            recipient="product-and-engineering",
            context={
                "query": report.query,
                "source_ids": [source.source_id for source in report.sources],
                "findings": [
                    {
                        "claim": finding.claim,
                        "evidence": finding.evidence,
                        "confidence": finding.confidence,
                    }
                    for finding in report.findings
                ],
            },
        )
        self._collaboration.handoff(handoff)
        return handoff

    @staticmethod
    def _define_product(
        ceo: CEOResult,
        research: ResearchReport,
    ) -> dict[str, Any]:
        return {
            "mission_id": ceo.mission.mission_id,
            "objective": ceo.plan.objective,
            "goals": ceo.plan.goals,
            "research_findings": research.finding_count,
            "acceptance": "Implementation must pass QA and security review.",
        }

    @staticmethod
    def _define_architecture(
        ceo: CEOResult,
        request: AutonomousProjectRequest,
    ) -> dict[str, Any]:
        return {
            "project_name": request.project_request.name,
            "objective": ceo.plan.objective,
            "task_count": len(request.tasks),
            "quality_gate": "QA -> security review -> GitHub release",
            "execution": "CompanyExecutionPipeline.run_end_to_end",
        }

    @staticmethod
    def _run_stage(
        stages: list[StageResult],
        name: str,
        action: Callable[[], Any],
    ) -> Any:
        try:
            result = action()
        except Exception as exc:
            stages.append(StageResult(name, StageStatus.FAILED, str(exc)))
            raise
        stages.append(StageResult(name, StageStatus.COMPLETED, "Stage completed."))
        return result

    @staticmethod
    async def _run_async_stage(
        stages: list[StageResult],
        name: str,
        action: Callable[[], Awaitable[Any]],
    ) -> Any:
        try:
            result = await action()
        except Exception as exc:
            stages.append(StageResult(name, StageStatus.FAILED, str(exc)))
            raise
        stages.append(StageResult(name, StageStatus.COMPLETED, "Stage completed."))
        return result

    async def _delivery_stage(
        self,
        stages: list[StageResult],
        name: str,
        hook: DeploymentHook | MonitoringHook | None,
        pipeline: PipelineResult,
    ) -> StageResult:
        if hook is None:
            result = StageResult(
                name,
                StageStatus.FAILED,
                f"{name} hook is required for M36 end-to-end delivery.",
            )
            stages.append(result)
            raise RuntimeError(result.detail)

        try:
            detail = hook(pipeline)
            if isawaitable(detail):
                detail = await detail
        except Exception as exc:
            result = StageResult(name, StageStatus.FAILED, str(exc))
            stages.append(result)
            raise

        result = StageResult(name, StageStatus.COMPLETED, str(detail))
        stages.append(result)
        return result

    @staticmethod
    def _build_dashboard(
        *,
        request: AutonomousProjectRequest,
        ceo: CEOResult,
        research: ResearchReport,
        pipeline: PipelineResult,
        deployment: StageResult,
        monitoring: StageResult,
        learning: LearningReport,
    ) -> DashboardSnapshot:
        dashboard = CompanyDashboard(
            {
                "company": lambda: {
                    "name": "AI Software Company",
                    "mode": "autonomous",
                },
                "projects": lambda: (
                    {
                        "id": pipeline.project.id,
                        "name": pipeline.project.name,
                        "status": pipeline.project.status.value,
                    },
                ),
                "agents": lambda: (
                    {"id": "ai-ceo", "status": "completed"},
                    {"id": "researcher", "status": "completed"},
                    {"id": "engineering", "status": "completed"},
                    {"id": "qa", "status": "completed"},
                    {"id": "security", "status": "completed"},
                ),
                "tasks": lambda: tuple(
                    {"id": task.title, "status": "completed"}
                    for task in request.tasks
                ),
                "runtime": lambda: {
                    "mission_id": ceo.mission.mission_id,
                    "project_status": pipeline.project.status.value,
                },
                "memory": lambda: {
                    "learning_signals": len(learning.signals),
                    "consolidated_knowledge": len(learning.consolidated_knowledge),
                },
                "qa": lambda: {
                    "status": pipeline.qa_result.status.value,
                },
                "security": lambda: {
                    "status": pipeline.review_result.status.value,
                },
                "deployments": lambda: {
                    "status": deployment.status.value,
                    "detail": deployment.detail,
                },
                "research": lambda: (
                    {
                        "query": research.query,
                        "sources": research.source_count,
                        "findings": research.finding_count,
                    },
                ),
                "metrics": lambda: {
                    "research_findings": research.finding_count,
                    "tasks": len(request.tasks),
                    "learning_signals": len(learning.signals),
                },
            }
        )
        return dashboard.snapshot()
