"""Deterministic quality, release, soak, and improvement acceptance gates.

These helpers deliberately consume evidence supplied by the execution pipeline;
they do not claim to run tests, review UI, scan code, or publish artifacts themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["critical", "high", "medium", "low"]
FindingStatus = Literal["open", "fixed", "accepted"]
GateStatus = Literal["passed", "blocked"]


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    finding_id: str
    severity: Severity
    status: FindingStatus
    summary: str


@dataclass(frozen=True, slots=True)
class QualityEvidence:
    requirement_coverage: float
    automated_checks_passed: bool
    security_checks_passed: bool
    responsive_checks_passed: bool
    accessibility_checks_passed: bool
    findings: tuple[ReviewFinding, ...] = ()


@dataclass(frozen=True, slots=True)
class GateDecision:
    status: GateStatus
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReleaseEvidence:
    candidate_revision: str
    tested_revision: str
    quality_gate: GateStatus
    security_gate: GateStatus
    approval_required: bool
    approval_granted: bool
    external_publish: bool = False


@dataclass(frozen=True, slots=True)
class MissionOutcome:
    mission_id: str
    status: Literal["completed", "blocked", "cancelled", "failed"]
    reason: str | None = None
    recovered: bool = False


@dataclass(frozen=True, slots=True)
class SoakEvidence:
    outcomes: tuple[MissionOutcome, ...]
    expected_mission_ids: tuple[str, ...]
    cross_mission_state_leak: bool = False
    false_success_detected: bool = False
    unrelated_work_starved: bool = False


@dataclass(frozen=True, slots=True)
class ImprovementMetrics:
    quality_score: float
    safety_score: float
    latency_seconds: float
    cost_units: float


def evaluate_product_quality(evidence: QualityEvidence) -> GateDecision:
    """Block approval when objective checks fail or serious findings remain."""
    reasons: list[str] = []
    if not 0.0 <= evidence.requirement_coverage <= 1.0:
        reasons.append("requirement coverage must be between 0 and 1")
    elif evidence.requirement_coverage < 1.0:
        reasons.append("requirements coverage is incomplete")
    for label, passed in (
        ("automated checks", evidence.automated_checks_passed),
        ("security checks", evidence.security_checks_passed),
        ("responsive checks", evidence.responsive_checks_passed),
        ("accessibility checks", evidence.accessibility_checks_passed),
    ):
        if not passed:
            reasons.append(f"{label} did not pass")
    seen: set[str] = set()
    for finding in evidence.findings:
        if not finding.finding_id.strip():
            reasons.append("review finding has an empty ID")
        elif finding.finding_id in seen:
            reasons.append(f"duplicate review finding ID: {finding.finding_id}")
        seen.add(finding.finding_id)
        if finding.status == "open" and finding.severity in ("critical", "high"):
            reasons.append(f"unresolved {finding.severity} finding: {finding.finding_id}")
    return GateDecision("blocked" if reasons else "passed", tuple(reasons))


def evaluate_release_readiness(evidence: ReleaseEvidence) -> GateDecision:
    """Bind release permission to the exact tested revision and required approval."""
    reasons: list[str] = []
    if not evidence.candidate_revision.strip():
        reasons.append("candidate revision is missing")
    if not evidence.tested_revision.strip():
        reasons.append("tested revision is missing")
    elif evidence.candidate_revision != evidence.tested_revision:
        reasons.append("candidate revision differs from tested revision")
    if evidence.quality_gate != "passed":
        reasons.append("quality gate has not passed")
    if evidence.security_gate != "passed":
        reasons.append("security gate has not passed")
    if evidence.approval_required and not evidence.approval_granted:
        reasons.append("required human approval is missing")
    if evidence.external_publish and not evidence.approval_granted:
        reasons.append("external publication requires explicit approval")
    return GateDecision("blocked" if reasons else "passed", tuple(dict.fromkeys(reasons)))


def evaluate_soak(evidence: SoakEvidence) -> GateDecision:
    """Require every expected mission to reach an evidence-backed terminal state."""
    reasons: list[str] = []
    expected = list(evidence.expected_mission_ids)
    actual = [outcome.mission_id for outcome in evidence.outcomes]
    if len(expected) != len(set(expected)):
        reasons.append("expected mission IDs contain duplicates")
    if len(actual) != len(set(actual)):
        reasons.append("soak outcomes contain duplicate mission IDs")
    if set(actual) != set(expected):
        reasons.append("soak outcomes do not match the expected mission set")
    if any(not outcome.reason and outcome.status != "completed" for outcome in evidence.outcomes):
        reasons.append("blocked, cancelled, or failed mission lacks a reason")
    if evidence.cross_mission_state_leak:
        reasons.append("cross-mission state leakage was detected")
    if evidence.false_success_detected:
        reasons.append("a mission was reported successful without acceptance evidence")
    if evidence.unrelated_work_starved:
        reasons.append("unrelated eligible work was starved")
    return GateDecision("blocked" if reasons else "passed", tuple(reasons))


def evaluate_improvement(
    baseline: ImprovementMetrics,
    candidate: ImprovementMetrics,
    *,
    minimum_quality_delta: float = 0.0,
    minimum_safety_delta: float = 0.0,
    maximum_latency_regression: float = 0.10,
    maximum_cost_regression: float = 0.10,
) -> GateDecision:
    """Reject quality/safety regressions and excessive latency or cost regressions."""
    reasons: list[str] = []
    values = (
        baseline.quality_score, baseline.safety_score, baseline.latency_seconds,
        baseline.cost_units, candidate.quality_score, candidate.safety_score,
        candidate.latency_seconds, candidate.cost_units,
    )
    if any(value < 0 for value in values):
        reasons.append("metrics cannot be negative")
    if candidate.quality_score - baseline.quality_score < minimum_quality_delta:
        reasons.append("quality improvement is below the required threshold")
    if candidate.safety_score - baseline.safety_score < minimum_safety_delta:
        reasons.append("safety improvement is below the required threshold")
    if baseline.latency_seconds == 0 and candidate.latency_seconds > 0:
        reasons.append("latency regression cannot be computed from a zero baseline")
    elif baseline.latency_seconds > 0 and candidate.latency_seconds > baseline.latency_seconds * (1 + maximum_latency_regression):
        reasons.append("latency regression exceeds the allowed threshold")
    if baseline.cost_units == 0 and candidate.cost_units > 0:
        reasons.append("cost regression cannot be computed from a zero baseline")
    elif baseline.cost_units > 0 and candidate.cost_units > baseline.cost_units * (1 + maximum_cost_regression):
        reasons.append("cost regression exceeds the allowed threshold")
    return GateDecision("blocked" if reasons else "passed", tuple(reasons))


def evaluate_integrated_acceptance(
    quality: QualityEvidence,
    release: ReleaseEvidence,
    soak: SoakEvidence,
    baseline: ImprovementMetrics,
    candidate: ImprovementMetrics,
) -> GateDecision:
    """Combine required delivery gates without discarding individual failure reasons."""
    decisions = (
        ("quality", evaluate_product_quality(quality)),
        ("release", evaluate_release_readiness(release)),
        ("soak", evaluate_soak(soak)),
        ("improvement", evaluate_improvement(baseline, candidate)),
    )
    reasons = tuple(
        f"{gate}: {reason}"
        for gate, decision in decisions
        for reason in decision.reasons
    )
    return GateDecision("blocked" if reasons else "passed", reasons)
