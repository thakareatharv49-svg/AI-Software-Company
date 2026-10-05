from __future__ import annotations

from company.ai.tool_calling import AIToolCallResponse
from company.operations import CompanyOperations
from company.research.engine import UrlResearchProvider


def test_company_cycle_connects_m32_to_m35(tmp_path) -> None:
    provider = UrlResearchProvider(
        ("https://example.com/docs",),
        fetcher=lambda _url: "Example research evidence.",
    )
    company = CompanyOperations(
        research_provider=provider,
        history_path=str(tmp_path / "history.jsonl"),
    )

    result = company.run_cycle(
        query="autonomous software",
        task_id="research-build",
        recipient="engineer",
        response=AIToolCallResponse(text="No tools required."),
    )

    assert result.research.source_count == 1
    assert result.handoff.recipient == "engineer"
    assert result.execution_run_id
    assert result.learning.signals[0].subject == "execution_success_rate"
    assert result.dashboard.runtime["executions"] == 1
    assert result.dashboard.research[0]["findings"] == 1
    assert len(company.history) == 1


def test_company_learning_uses_persisted_execution_history(tmp_path) -> None:
    provider = UrlResearchProvider(
        ("https://example.com",),
        fetcher=lambda _url: "evidence",
    )
    company = CompanyOperations(
        research_provider=provider,
        history_path=str(tmp_path / "history.jsonl"),
    )

    company.execute(AIToolCallResponse(text="first"))
    company.execute(AIToolCallResponse(text="second"))

    learning = company.learn()

    assert learning.signals[0].score == 1.0
    assert "Observed 2 executions" in learning.consolidated_knowledge[0]
