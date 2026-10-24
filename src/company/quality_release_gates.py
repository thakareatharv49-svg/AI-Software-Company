"""Deterministic quality, release, soak, and improvement acceptance gates.

These helpers deliberately consume evidence supplied by the execution pipeline;
they do not claim to run tests, review UI, scan code, or publish artifacts themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
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
    candidate_revision: str | None = None


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
    candidate_artifact_digest: str | None = None
    tested_artifact_digest: str | None = None


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
    candidate_revision: str | None = None


@dataclass(frozen=True, slots=True)
class ImprovementMetrics:
    quality_score: float
    safety_score: float
    latency_seconds: float
    cost_units: float
    candidate_revision: str | None = None


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
    candidate_digest = (evidence.candidate_artifact_digest or "").strip()
    tested_digest = (evidence.tested_artifact_digest or "").strip()
    if evidence.external_publish and (not candidate_digest or not tested_digest):
        reasons.append("external publication requires candidate and tested artifact digests")
    if candidate_digest and tested_digest and candidate_digest != tested_digest:
        reasons.append("candidate artifact digest differs from tested artifact digest")
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
    if any(not math.isfinite(value) for value in values):
        reasons.append("metrics must be finite numbers")
    if any(value < 0 for value in values):
        reasons.append("metrics cannot be negative")
    if any(value > 1 for value in (baseline.quality_score, baseline.safety_score, candidate.quality_score, candidate.safety_score)):
        reasons.append("quality and safety scores must be between 0 and 1")
    thresholds = (
        minimum_quality_delta, minimum_safety_delta,
        maximum_latency_regression, maximum_cost_regression,
    )
    if any(not math.isfinite(value) or value < 0 for value in thresholds):
        reasons.append("regression thresholds must be finite and non-negative")
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
    reasons = [
        f"{gate}: {reason}"
        for gate, decision in decisions
        for reason in decision.reasons
    ]
    expected_revision = release.candidate_revision.strip()
    if not expected_revision:
        reasons.append("integrity: candidate revision is missing")
    if quality.candidate_revision != expected_revision:
        reasons.append("integrity: quality evidence does not match candidate revision")
    if soak.candidate_revision != expected_revision:
        reasons.append("integrity: soak evidence does not match candidate revision")
    if candidate.candidate_revision != expected_revision:
        reasons.append("integrity: improvement metrics do not match candidate revision")
    return GateDecision("blocked" if reasons else "passed", tuple(reasons))


def evaluate_factory_plan_quality(
    plan: object,
    *,
    candidate_revision: str,
    requirement_coverage: float,
    responsive_checks_passed: bool,
    accessibility_checks_passed: bool,
    findings: tuple[ReviewFinding, ...] = (),
) -> GateDecision:
    """Adapt persisted factory-plan QA/security evidence to the product-quality gate.

    Browser responsiveness/accessibility are explicit inputs because a generic
    Python QA result cannot prove those product properties.
    """
    contract = getattr(plan, "requirements_contract", None)
    requirements = getattr(contract, "functional_requirements", ()) if contract else ()
    criteria = getattr(plan, "acceptance_criteria", ()) or ()
    # Coverage is supplied by a requirement-by-requirement review; the mere
    # existence of requirements must never be mistaken for complete coverage.
    coverage = requirement_coverage if (requirements or criteria) else 0.0

    qa_status = str(getattr(plan, "qa_status", "") or "").strip().lower()
    security_status = str(getattr(plan, "security_status", "") or "").strip().lower()
    qa_evidence = str(getattr(plan, "qa_evidence", "") or "").strip()
    security_evidence = str(getattr(plan, "security_evidence", "") or "").strip()

    qa_passed = qa_status in {"passed", "pass", "success", "succeeded"} and bool(qa_evidence)
    security_passed = (
        security_status in {"passed", "pass", "success", "succeeded", "approved"}
        and bool(security_evidence)
    )
    # A successful QA run is evidence for execution, not by itself proof that
    # every requirement is covered. Missing requirements are rejected above.
    evidence = QualityEvidence(
        requirement_coverage=coverage,
        automated_checks_passed=qa_passed,
        security_checks_passed=security_passed,
        responsive_checks_passed=responsive_checks_passed,
        accessibility_checks_passed=accessibility_checks_passed,
        findings=findings,
        candidate_revision=candidate_revision,
    )
    return evaluate_product_quality(evidence)
