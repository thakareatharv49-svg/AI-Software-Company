from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LearningSignal:
    category: str
    subject: str
    score: float
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class LearningReport:
    signals: tuple[LearningSignal, ...]
    consolidated_knowledge: tuple[str, ...]


class LearningEngine:
    """Turns execution experience into bounded, inspectable improvement signals."""

    def analyze_executions(self, records: list[dict[str, object]]) -> LearningReport:
        if not records:
            return LearningReport((), ())

        successes = [item for item in records if bool(item.get("success"))]
        failures = [item for item in records if not bool(item.get("success"))]
        rate = len(successes) / len(records)

        signals = [
            LearningSignal(
                category="success_analysis",
                subject="execution_success_rate",
                score=rate,
                evidence=f"{len(successes)}/{len(records)} executions succeeded",
                recommendation=(
                    "Preserve the current strategy."
                    if rate >= 0.8
                    else "Review unsuccessful execution paths."
                ),
            )
        ]

        if failures:
            signals.append(
                LearningSignal(
                    category="failure_analysis",
                    subject="execution_failures",
                    score=float(len(failures)),
                    evidence=f"{len(failures)} executions failed",
                    recommendation="Inspect failure causes before increasing autonomy.",
                )
            )

        return LearningReport(
            tuple(signals),
            (f"Observed {len(records)} executions with success rate {rate:.2f}.",),
        )

    def evaluate_agent_performance(
        self,
        agent_results: dict[str, list[bool]],
    ) -> LearningReport:
        signals: list[LearningSignal] = []
        knowledge: list[str] = []

        for agent, results in sorted(agent_results.items()):
            if not results:
                continue
            rate = sum(results) / len(results)
            signals.append(
                LearningSignal(
                    category="agent_performance",
                    subject=agent,
                    score=rate,
                    evidence=f"{sum(results)}/{len(results)} successful",
                    recommendation=(
                        "Retain specialization."
                        if rate >= 0.8
                        else "Review agent strategy and tooling."
                    ),
                )
            )
            knowledge.append(f"{agent} success rate: {rate:.2f}")

        return LearningReport(tuple(signals), tuple(knowledge))

    def consolidate(self, reports: tuple[LearningReport, ...]) -> tuple[str, ...]:
        knowledge: list[str] = []
        seen: set[str] = set()
        for report in reports:
            for item in report.consolidated_knowledge:
                if item not in seen:
                    seen.add(item)
                    knowledge.append(item)
        return tuple(knowledge)
