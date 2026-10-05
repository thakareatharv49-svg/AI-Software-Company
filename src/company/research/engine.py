from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class ResearchSource:
    source_id: str
    title: str
    url: str
    publisher: str = ""
    content: str = ""

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.url.strip():
            raise ValueError("url must not be empty")


@dataclass(frozen=True)
class ResearchFinding:
    claim: str
    evidence: str
    source_ids: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        if not self.claim.strip():
            raise ValueError("claim must not be empty")
        if not self.source_ids:
            raise ValueError("source_ids must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ResearchReport:
    query: str
    findings: tuple[ResearchFinding, ...]
    sources: tuple[ResearchSource, ...]
    generated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def finding_count(self) -> int:
        return len(self.findings)


class ResearchProvider(Protocol):
    def search(self, query: str) -> tuple[ResearchSource, ...]:
        ...


class StaticResearchProvider:
    """Deterministic provider used by the core engine and tests.

    Real web/API providers can implement ResearchProvider without changing
    the research engine.
    """

    def __init__(self, sources: tuple[ResearchSource, ...] = ()) -> None:
        self._sources = tuple(sources)

    def search(self, query: str) -> tuple[ResearchSource, ...]:
        terms = {term.lower() for term in query.split() if term.strip()}
        if not terms:
            return ()

        matches = []
        for source in self._sources:
            haystack = " ".join(
                [source.title, source.publisher, source.content]
            ).lower()
            if all(term in haystack for term in terms):
                matches.append(source)

        return tuple(matches)


class ResearchEngine:
    """Builds validated, source-backed research reports."""

    def __init__(self, provider: ResearchProvider) -> None:
        self._provider = provider

    def research(self, query: str) -> ResearchReport:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")

        sources = self._provider.search(normalized_query)
        findings = tuple(
            self._finding_from_source(source)
            for source in sources
        )

        return ResearchReport(
            query=normalized_query,
            findings=findings,
            sources=sources,
        )

    @staticmethod
    def _finding_from_source(source: ResearchSource) -> ResearchFinding:
        evidence = source.content.strip() or source.title
        return ResearchFinding(
            claim=source.title,
            evidence=evidence,
            source_ids=(source.source_id,),
            confidence=1.0 if source.content.strip() else 0.5,
        )

    @staticmethod
    def validate_sources(sources: tuple[ResearchSource, ...]) -> bool:
        seen: set[str] = set()
        for source in sources:
            if source.source_id in seen:
                return False
            seen.add(source.source_id)
        return True
