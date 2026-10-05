from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    category: str
    expected: bool


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    category: str
    passed: bool


@dataclass(frozen=True)
class BenchmarkReport:
    results: tuple[BenchmarkResult, ...]

    @property
    def score(self) -> float:
        if not self.results:
            return 0.0
        return mean(result.passed for result in self.results)

    def category_scores(self) -> dict[str, float]:
        categories = sorted({result.category for result in self.results})
        return {
            category: mean(
                result.passed
                for result in self.results
                if result.category == category
            )
            for category in categories
        }


class CompanyEvaluator:
    """M40 deterministic evaluation and regression benchmarking."""

    def evaluate(
        self,
        cases: tuple[BenchmarkCase, ...],
        observations: dict[str, bool],
    ) -> BenchmarkReport:
        results = tuple(
            BenchmarkResult(
                case.name,
                case.category,
                observations.get(case.name, False) == case.expected,
            )
            for case in cases
        )
        return BenchmarkReport(results)

    def regression_gate(self, current: BenchmarkReport, baseline_score: float) -> bool:
        if not 0.0 <= baseline_score <= 1.0:
            raise ValueError("baseline_score must be between 0 and 1")
        return current.score >= baseline_score
