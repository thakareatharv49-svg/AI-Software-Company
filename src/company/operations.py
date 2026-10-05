from __future__ import annotations

from dataclasses import dataclass

from company.ai.coordinator import AIExecutionCoordinator, build_ai_execution_coordinator
from company.ai.history import AIExecutionHistoryRecord
from company.ai.model import AIResponse
from company.ai.tool_calling import AIToolCallResponse
from company.collaboration.bus import CollaborationBus, Handoff
from company.dashboard.service import CompanyDashboard, DashboardSnapshot
from company.learning.engine import LearningEngine, LearningReport
from company.research.engine import ResearchEngine, ResearchProvider, ResearchReport


@dataclass(frozen=True)
class CompanyCycleResult:
    research: ResearchReport
    handoff: Handoff
    execution_run_id: str
    learning: LearningReport
    dashboard: DashboardSnapshot


class CompanyOperations:
    """Integrated operating surface for the autonomous software company.

    This is the bridge between the milestone subsystems: research feeds
    collaboration, execution creates durable history, learning analyzes that
    history, and the dashboard reads the resulting live company state.
    """

    def __init__(
        self,
        *,
        research_provider: ResearchProvider,
        history_path: str,
    ) -> None:
        self._research = ResearchEngine(research_provider)
        self._collaboration = CollaborationBus()
        self._coordinator: AIExecutionCoordinator = build_ai_execution_coordinator(
            history_path
        )
        self._learning = LearningEngine()
        self._reports: list[ResearchReport] = []
        self._completed_tasks: set[str] = set()

    @property
    def collaboration(self) -> CollaborationBus:
        return self._collaboration

    @property
    def history(self) -> tuple[AIExecutionHistoryRecord, ...]:
        return self._coordinator.history.list()

    def research(self, query: str) -> ResearchReport:
        report = self._research.research(query)
        self._reports.append(report)
        return report

    def handoff_research(
        self,
        *,
        task_id: str,
        recipient: str,
        report: ResearchReport,
    ) -> Handoff:
        context = {
            "query": report.query,
            "finding_count": report.finding_count,
            "sources": [source.source_id for source in report.sources],
            "findings": [
                {
                    "claim": finding.claim,
                    "evidence": finding.evidence,
                    "confidence": finding.confidence,
                }
                for finding in report.findings
            ],
        }
        handoff = Handoff(
            task_id=task_id,
            sender="researcher",
            recipient=recipient,
            context=context,
        )
        self._collaboration.handoff(handoff)
        return handoff

    def execute(
        self,
        response: AIToolCallResponse,
        *,
        actor: str = "company",
    ):
        result = self._coordinator.execute(
            response,
            context=self._context(actor),
        )
        if not result.loop.stopped_by_limit:
            self._completed_tasks.add(result.run_id)
        return result

    def learn(self) -> LearningReport:
        records = [
            {
                "success": record.success,
                "actor": record.actor,
                "run_id": record.run_id,
                "rounds": record.rounds,
                "tool_calls": record.tool_calls,
            }
            for record in self.history
        ]
        return self._learning.analyze_executions(records)

    def dashboard(self) -> DashboardSnapshot:
        learning = self.learn()
        dashboard = CompanyDashboard(
            {
                "company": lambda: {
                    "name": "AI Software Company",
                    "mode": "autonomous",
                },
                "projects": lambda: (
                    {"id": "autonomous-company", "status": "active"},
                ),
                "agents": lambda: (
                    {"id": "researcher", "status": "available"},
                    {"id": "company", "status": "available"},
                ),
                "tasks": lambda: tuple(
                    {"id": record.run_id, "status": "completed" if record.success else "failed"}
                    for record in self.history
                ),
                "runtime": lambda: {
                    "executions": len(self.history),
                    "successful_executions": sum(record.success for record in self.history),
                },
                "memory": lambda: {
                    "history_records": len(self.history),
                    "learning_signals": len(learning.signals),
                },
                "research": lambda: tuple(
                    {
                        "query": report.query,
                        "sources": report.source_count,
                        "findings": report.finding_count,
                    }
                    for report in self._reports
                ),
                "failures": lambda: tuple(
                    {"run_id": record.run_id, "actor": record.actor}
                    for record in self.history
                    if not record.success
                ),
                "metrics": lambda: {
                    "success_rate": (
                        sum(record.success for record in self.history) / len(self.history)
                        if self.history
                        else 0.0
                    )
                },
            }
        )
        return dashboard.snapshot()

    def run_cycle(
        self,
        *,
        query: str,
        task_id: str,
        recipient: str,
        response: AIToolCallResponse,
        actor: str = "company",
    ) -> CompanyCycleResult:
        report = self.research(query)
        handoff = self.handoff_research(
            task_id=task_id,
            recipient=recipient,
            report=report,
        )
        result = self.execute(response, actor=actor)
        learning = self.learn()
        snapshot = self.dashboard()
        return CompanyCycleResult(
            research=report,
            handoff=handoff,
            execution_run_id=result.run_id,
            learning=learning,
            dashboard=snapshot,
        )

    @staticmethod
    def _context(actor: str):
        from company.ai.context import AIExecutionContext

        return AIExecutionContext(actor=actor)
