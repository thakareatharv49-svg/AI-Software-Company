from __future__ import annotations

from dataclasses import dataclass

from src.company.research.engine import ResearchReport


@dataclass(frozen=True, slots=True)
class ProductCandidate:
    name: str
    problem: str
    target_user: str
    score: float
    evidence_count: int
    confidence: float


class ProductDiscovery:
    """Generates product candidates from source-backed research."""

    def discover(
        self,
        reports: list[ResearchReport],
        target_user: str,
    ) -> list[ProductCandidate]:
        candidates = []
        for report in reports:
            evidence_count = report.source_count
            candidates.append(
                ProductCandidate(
                    name=f"{report.query.title()} Solution",
                    problem=(
                        report.findings[0].claim
                        if report.findings
                        else report.query
                    ),
                    target_user=target_user,
                    score=sum(f.confidence for f in report.findings),
                    evidence_count=evidence_count,
                    confidence=(
                        sum(f.confidence for f in report.findings)
                        / len(report.findings)
                        if report.findings
                        else 0.0
                    ),
                )
            )
        return sorted(
            candidates,
            key=lambda item: (item.score, item.evidence_count),
            reverse=True,
        )
