from __future__ import annotations

import pytest

from company.research.engine import (
    ResearchEngine,
    ResearchSource,
    StaticResearchProvider,
)


def _sources() -> tuple[ResearchSource, ...]:
    return (
        ResearchSource(
            source_id="docs-1",
            title="Python documentation",
            url="https://docs.python.org/",
            publisher="Python",
            content="Python is a programming language.",
        ),
        ResearchSource(
            source_id="docs-2",
            title="Python typing documentation",
            url="https://docs.python.org/typing/",
            publisher="Python",
            content="Typing provides type hints.",
        ),
    )


def test_research_returns_source_backed_findings() -> None:
    engine = ResearchEngine(StaticResearchProvider(_sources()))

    report = engine.research("Python documentation")

    assert report.query == "Python documentation"
    assert report.source_count == 1
    assert report.finding_count == 1
    assert report.findings[0].source_ids == ("docs-1",)
    assert report.findings[0].confidence == 1.0


def test_research_is_case_insensitive() -> None:
    engine = ResearchEngine(StaticResearchProvider(_sources()))

    report = engine.research("PYTHON DOCUMENTATION")

    assert report.finding_count == 1


def test_empty_query_is_rejected() -> None:
    engine = ResearchEngine(StaticResearchProvider())

    with pytest.raises(ValueError, match="query"):
        engine.research("")


def test_source_validation_rejects_duplicates() -> None:
    source = _sources()[0]

    assert ResearchEngine.validate_sources((source, source)) is False
    assert ResearchEngine.validate_sources((source,)) is True
