import pytest

from src.company.project_factory import ProjectFactory
from src.company.quality_release_gates import (
    ImprovementMetrics,
    MissionOutcome,
    QualityEvidence,
    ReleaseEvidence,
    ReviewFinding,
    SoakEvidence,
    evaluate_improvement,
    evaluate_integrated_acceptance,
    evaluate_factory_plan_quality,
    evaluate_product_quality,
    evaluate_release_readiness,
    evaluate_soak,
)


def good_quality(**overrides):
    values = {
        "requirement_coverage": 1.0,
        "automated_checks_passed": True,
        "security_checks_passed": True,
        "responsive_checks_passed": True,
        "accessibility_checks_passed": True,
        "findings": (),
    }
    values.update(overrides)
    return QualityEvidence(**values)


def test_quality_gate_passes_only_with_complete_evidence():
    assert evaluate_product_quality(good_quality()).status == "passed"
    decision = evaluate_product_quality(
        good_quality(requirement_coverage=0.8, security_checks_passed=False)
    )
    assert decision.status == "blocked"
    assert any("coverage" in reason for reason in decision.reasons)
    assert any("security" in reason for reason in decision.reasons)


@pytest.mark.parametrize("severity", ["critical", "high"])
def test_open_serious_review_finding_blocks_approval(severity):
    finding = ReviewFinding("F-1", severity, "open", "unsafe behavior")
    decision = evaluate_product_quality(good_quality(findings=(finding,)))
    assert decision.status == "blocked"
    assert any("F-1" in reason for reason in decision.reasons)


def test_closed_or_low_severity_findings_do_not_block_by_themselves():
    findings = (
        ReviewFinding("F-1", "critical", "fixed", "fixed and retested"),
        ReviewFinding("F-2", "low", "open", "minor copy issue"),
    )
    assert evaluate_product_quality(good_quality(findings=findings)).status == "passed"


def test_duplicate_finding_ids_are_rejected():
    findings = (
        ReviewFinding("F-1", "low", "open", "first"),
        ReviewFinding("F-1", "low", "fixed", "duplicate"),
    )
    assert evaluate_product_quality(good_quality(findings=findings)).status == "blocked"


def test_release_gate_binds_approval_to_exact_tested_revision():
    good = ReleaseEvidence("abc123", "abc123", "passed", "passed", True, True, True, "sha256:artifact-a", "sha256:artifact-a")
    assert evaluate_release_readiness(good).status == "passed"
    changed = ReleaseEvidence("def456", "abc123", "passed", "passed", True, True, True)
    decision = evaluate_release_readiness(changed)
    assert decision.status == "blocked"
    assert any("differs" in reason for reason in decision.reasons)


def test_release_gate_blocks_failed_security_and_missing_approval():
    evidence = ReleaseEvidence("abc123", "abc123", "passed", "blocked", True, False, True)
    decision = evaluate_release_readiness(evidence)
    assert decision.status == "blocked"
    assert any("security" in reason for reason in decision.reasons)
    assert any("approval" in reason for reason in decision.reasons)


def test_soak_requires_exact_mission_set_and_no_state_leaks():
    expected = ("one", "two")
    outcomes = (
        MissionOutcome("one", "completed"),
        MissionOutcome("two", "blocked", "budget limit reached", recovered=True),
    )
    assert evaluate_soak(SoakEvidence(outcomes, expected)).status == "passed"
    decision = evaluate_soak(
        SoakEvidence(outcomes, expected, cross_mission_state_leak=True)
    )
    assert decision.status == "blocked"
    assert any("leakage" in reason for reason in decision.reasons)


def test_soak_rejects_false_success_duplicate_and_unexplained_failure():
    evidence = SoakEvidence(
        outcomes=(
            MissionOutcome("one", "completed"),
            MissionOutcome("one", "failed"),
            MissionOutcome("two", "failed"),
        ),
        expected_mission_ids=("one", "two"),
        false_success_detected=True,
    )
    decision = evaluate_soak(evidence)
    assert decision.status == "blocked"
    assert any("duplicate" in reason for reason in decision.reasons)
    assert any("without acceptance" in reason for reason in decision.reasons)
    assert any("lacks a reason" in reason for reason in decision.reasons)


def test_improvement_gate_rejects_quality_or_safety_regressions():
    baseline = ImprovementMetrics(0.8, 0.9, 10, 100)
    candidate = ImprovementMetrics(0.7, 0.85, 10, 100)
    decision = evaluate_improvement(baseline, candidate)
    assert decision.status == "blocked"
    assert any("quality" in reason for reason in decision.reasons)
    assert any("safety" in reason for reason in decision.reasons)


def test_improvement_gate_enforces_latency_and_cost_budgets():
    baseline = ImprovementMetrics(0.8, 0.9, 10, 100)
    candidate = ImprovementMetrics(0.9, 0.95, 12, 120)
    decision = evaluate_improvement(baseline, candidate)
    assert decision.status == "blocked"
    assert any("latency" in reason for reason in decision.reasons)
    assert any("cost" in reason for reason in decision.reasons)


def test_improvement_gate_passes_when_all_metrics_are_within_bounds():
    baseline = ImprovementMetrics(0.8, 0.9, 10, 100)
    candidate = ImprovementMetrics(0.85, 0.92, 10.5, 105)
    assert evaluate_improvement(baseline, candidate).status == "passed"


def test_integrated_acceptance_blocks_when_any_required_gate_fails():
    quality = good_quality()
    release = ReleaseEvidence("candidate", "old-tested", "passed", "passed", False, False)
    soak = SoakEvidence((MissionOutcome("one", "completed"),), ("one",))
    baseline = ImprovementMetrics(0.8, 0.9, 10, 100)
    candidate = ImprovementMetrics(0.9, 0.95, 10, 100)
    decision = evaluate_integrated_acceptance(quality, release, soak, baseline, candidate)
    assert decision.status == "blocked"
    assert any("release:" in reason and "differs" in reason for reason in decision.reasons)


def test_integrated_acceptance_passes_only_when_all_gates_pass():
    quality = good_quality(candidate_revision="candidate")
    release = ReleaseEvidence("candidate", "candidate", "passed", "passed", True, True)
    soak = SoakEvidence(
        (MissionOutcome("one", "completed"), MissionOutcome("two", "blocked", "cancelled by policy")),
        ("one", "two"),
        candidate_revision="candidate",
    )
    baseline = ImprovementMetrics(0.8, 0.9, 10, 100)
    candidate = ImprovementMetrics(0.85, 0.92, 10.5, 105, candidate_revision="candidate")
    decision = evaluate_integrated_acceptance(quality, release, soak, baseline, candidate)
    assert decision.status == "passed"
    assert decision.reasons == ()


def test_factory_plan_adapter_requires_real_qa_and_security_evidence():
    from types import SimpleNamespace

    plan = SimpleNamespace(
        requirements_contract=SimpleNamespace(functional_requirements=[object()]),
        acceptance_criteria=["app starts"],
        qa_status="passed",
        qa_evidence="pytest: 12 passed",
        security_status="passed",
        security_evidence="scanner: no findings",
    )
    decision = evaluate_factory_plan_quality(
        plan, candidate_revision="rev-a", requirement_coverage=1.0,
        responsive_checks_passed=True, accessibility_checks_passed=True
    )
    assert decision.status == "passed"

    plan.security_evidence = ""
    decision = evaluate_factory_plan_quality(
        plan, candidate_revision="rev-a", requirement_coverage=1.0,
        responsive_checks_passed=True, accessibility_checks_passed=True
    )
    assert decision.status == "blocked"
    assert any("security checks" in reason for reason in decision.reasons)


def test_factory_plan_adapter_does_not_infer_responsive_or_accessibility():
    from types import SimpleNamespace

    plan = SimpleNamespace(
        requirements_contract=None,
        acceptance_criteria=["app starts"],
        qa_status="passed",
        qa_evidence="test command succeeded",
        security_status="passed",
        security_evidence="security scan succeeded",
    )
    decision = evaluate_factory_plan_quality(
        plan, candidate_revision="rev-a", requirement_coverage=1.0,
        responsive_checks_passed=False, accessibility_checks_passed=False
    )
    assert decision.status == "blocked"
    assert any("responsive" in reason for reason in decision.reasons)
    assert any("accessibility" in reason for reason in decision.reasons)


def test_integrated_acceptance_blocks_stale_soak_or_improvement_evidence():
    quality = good_quality(candidate_revision="new")
    release = ReleaseEvidence("new", "new", "passed", "passed", True, True)
    soak = SoakEvidence((MissionOutcome("one", "completed"),), ("one",), candidate_revision="old")
    baseline = ImprovementMetrics(0.8, 0.9, 10, 100)
    candidate = ImprovementMetrics(0.85, 0.92, 10, 100, candidate_revision="old")
    decision = evaluate_integrated_acceptance(
        quality, release, soak, baseline, candidate
    )
    assert decision.status == "blocked"
    assert any("soak evidence does not match" in reason for reason in decision.reasons)
    assert any("improvement metrics do not match" in reason for reason in decision.reasons)


def test_factory_records_acceptance_and_blocks_changed_revision():
    from types import SimpleNamespace

    saved = []

    class AuditStore:
        def append(self, entry):
            saved.append(entry)

    factory = ProjectFactory(
        orchestrator=SimpleNamespace(),
        controller=SimpleNamespace(),
        pipeline=SimpleNamespace(),
        audit_store=AuditStore(),
    )
    project = SimpleNamespace(
        mission=SimpleNamespace(id="mission-1", name="release candidate")
    )
    decision = evaluate_product_quality(good_quality())
    record = factory.record_delivery_acceptance(
        project,
        candidate_revision="new-sha",
        tested_revision="old-sha",
        decision=decision,
    )
    assert record["status"] == "blocked"
    assert any("differs" in reason for reason in record["reasons"])
    assert saved[-1].event_type == "DELIVERY_ACCEPTANCE_DECISION"
    assert saved[-1].status == "blocked"


def test_factory_acceptance_audit_records_only_same_tested_revision():
    from types import SimpleNamespace

    saved = []

    class AuditStore:
        def append(self, entry):
            saved.append(entry)

    factory = ProjectFactory(
        orchestrator=SimpleNamespace(),
        controller=SimpleNamespace(),
        pipeline=SimpleNamespace(),
        audit_store=AuditStore(),
    )
    project = SimpleNamespace(
        mission=SimpleNamespace(id="mission-2", name="approved candidate")
    )
    decision = evaluate_product_quality(good_quality())
    record = factory.record_delivery_acceptance(
        project,
        candidate_revision="same-sha",
        tested_revision="same-sha",
        decision=decision,
    )
    assert record["status"] == "passed"
    assert saved[-1].metadata["candidate_revision"] == "same-sha"


def test_external_release_requires_matching_artifact_digests():
    missing = ReleaseEvidence("rev", "rev", "passed", "passed", True, True, True)
    decision = evaluate_release_readiness(missing)
    assert decision.status == "blocked"
    assert any("requires candidate and tested artifact digests" in reason for reason in decision.reasons)

    mismatched = ReleaseEvidence(
        "rev", "rev", "passed", "passed", True, True, True,
        "sha256:candidate", "sha256:tested",
    )
    decision = evaluate_release_readiness(mismatched)
    assert decision.status == "blocked"
    assert any("digest differs" in reason for reason in decision.reasons)
