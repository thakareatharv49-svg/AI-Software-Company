from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Protocol
from urllib.request import Request, urlopen


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
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

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
    """Deterministic provider used by the core engine and tests."""

    def __init__(self, sources: tuple[ResearchSource, ...] = ()) -> None:
        self._sources = tuple(sources)

    def search(self, query: str) -> tuple[ResearchSource, ...]:
        normalized = " ".join(query.split()).lower()
        if not normalized:
            return ()

        exact = tuple(
            source for source in self._sources
            if " ".join(source.title.split()).lower() == normalized
        )
        if exact:
            return exact

        terms = {term for term in normalized.split() if term}
        matches = []
        for source in self._sources:
            haystack = " ".join(
                [source.title, source.publisher, source.content]
            ).lower()
            if all(term in haystack for term in terms):
                matches.append(source)

        return tuple(matches)


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return " ".join(self._parts)


class UrlResearchProvider:
    """Fetches a supplied set of real URLs and exposes them as research sources."""

    def __init__(
        self,
        urls: tuple[str, ...],
        *,
        fetcher=None,
    ) -> None:
        self._urls = tuple(urls)
        self._fetcher = fetcher or self._fetch

    def search(self, query: str) -> tuple[ResearchSource, ...]:
        if not query.strip():
            return ()

        sources: list[ResearchSource] = []
        for index, url in enumerate(self._urls, start=1):
            content = self._fetcher(url)
            sources.append(
                ResearchSource(
                    source_id=f"url-{index}",
                    title=f"Research source {index}",
                    url=url,
                    content=content,
                )
            )
        return tuple(sources)

    @staticmethod
    def _fetch(url: str) -> str:
        request = Request(
            url,
            headers={"User-Agent": "AI-Software-Company-Research/1.0"},
        )
        with urlopen(request, timeout=10) as response:
            raw = response.read()
        parser = _HTMLTextParser()
        parser.feed(raw.decode("utf-8", errors="replace"))
        return parser.text()


class ResearchEngine:
    """Builds validated, source-backed research reports."""

    def __init__(self, provider: ResearchProvider) -> None:
        self._provider = provider

    def research(self, query: str) -> ResearchReport:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")

        sources = self._provider.search(normalized_query)
        if not self.validate_sources(sources):
            raise ValueError("duplicate research source ids detected")

        findings = tuple(self._finding_from_source(source) for source in sources)

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
