from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from company.acceptance import AcceptanceStatus, AutonomousCompanyAcceptance
from company.autonomous_project import StageResult, StageStatus


def test_acceptance_requires_completed_autonomous_stages() -> None:
    acceptance = AutonomousCompanyAcceptance()
    assert "ai_ceo" in acceptance.REQUIRED_STAGES
    assert AcceptanceStatus.PASSED.value == "passed"


def test_acceptance_stage_names_are_stable() -> None:
    stage = StageResult("deployment", StageStatus.COMPLETED, "ok")
    changed = replace(stage, status=StageStatus.FAILED)
    assert stage.status == StageStatus.COMPLETED
    assert changed.status == StageStatus.FAILED


def _accepted_result(
    stage_names: tuple[str, ...] | None = None,
    *,
    objective: str = "Build a Notes App browser application",
    browser_preview: bool = True,
    project_name: str = "Notes App",
):
    names = stage_names or AutonomousCompanyAcceptance.REQUIRED_STAGES
    return SimpleNamespace(
        ceo=SimpleNamespace(
            decision=SimpleNamespace(requires_human=False),
            mission=SimpleNamespace(
                status=SimpleNamespace(value="approved"),
                objective=objective,
            ),
        ),
        stages=[
            StageResult(name, StageStatus.COMPLETED, "ok")
            for name in names
        ],
        pipeline=SimpleNamespace(
            project=SimpleNamespace(id="project-1", name=project_name),
            qa_result=SimpleNamespace(
                status=SimpleNamespace(value="passed"),
                exit_code=0,
            ),
            qa_checks=[
                {
                    "kind": "configured",
                    "status": "passed",
                    "exit_code": 0,
                    "duration_ms": 10,
                    "command": ["pytest", "-q"],
                },
            ],
            review_result=SimpleNamespace(status=SimpleNamespace(value="approved")),
            browser_preview=browser_preview,
            browser_acceptance={
                "status": "passed",
                "routes_checked": ["/"],
                "interactions_checked": ["Save"],
                "detail": "Browser acceptance passed.",
            },
        ),
        deployment=SimpleNamespace(status=SimpleNamespace(value="completed")),
        monitoring=SimpleNamespace(status=SimpleNamespace(value="completed")),
        learning=SimpleNamespace(signals=[{"kind": "success"}]),
    )


def test_acceptance_passes_only_when_all_delivery_checks_pass() -> None:
    report = AutonomousCompanyAcceptance().evaluate(_accepted_result())

    assert report.passed
    assert report.status == AcceptanceStatus.PASSED


def test_acceptance_rejects_missing_required_lifecycle_stage() -> None:
    result = _accepted_result(
        tuple(
            name
            for name in AutonomousCompanyAcceptance.REQUIRED_STAGES
            if name != "deployment"
        )
    )

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "deployment" in failed


def test_acceptance_rejects_app_without_browser_preview() -> None:
    result = _accepted_result(browser_preview=False)

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "browser_preview_available" in failed


def test_acceptance_does_not_require_preview_for_cli_missions() -> None:
    result = _accepted_result(
        objective="Build a command-line Python utility",
        browser_preview=False,
    )

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert report.passed
    assert "browser_preview_available" not in {
        check.name for check in report.checks
    }



def test_acceptance_uses_project_name_when_objective_is_vague() -> None:
    result = _accepted_result(
        objective="Build this product",
        browser_preview=False,
        project_name="Notes App",
    )

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "browser_preview_available" in failed



def test_acceptance_rejects_qa_status_passed_with_nonzero_exit_code() -> None:
    result = _accepted_result()
    result.pipeline.qa_result.exit_code = 1

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "qa_exit_code_zero" in failed


def test_acceptance_rejects_missing_or_empty_qa_command_ledger() -> None:
    result = _accepted_result()
    result.pipeline.qa_checks = []

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "qa_evidence_complete" in failed


def test_acceptance_rejects_any_failed_recorded_qa_command() -> None:
    result = _accepted_result()
    result.pipeline.qa_checks.append(
        {
            "kind": "integration",
            "status": "failed",
            "exit_code": 1,
            "duration_ms": 20,
            "command": ["pytest", "tests/integration"],
        }
    )

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "qa_evidence_complete" in failed


def test_acceptance_rejects_web_app_without_browser_acceptance_evidence() -> None:
    result = _accepted_result()
    del result.pipeline.browser_acceptance

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "browser_acceptance_passed" in failed


def test_acceptance_rejects_failed_browser_acceptance() -> None:
    result = _accepted_result()
    result.pipeline.browser_acceptance = {
        "status": "failed",
        "routes_checked": ["/"],
        "interactions_checked": [],
        "detail": "Button did not respond.",
    }

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "browser_acceptance_passed" in failed


def test_acceptance_requires_qa_exit_code_to_be_integer_zero() -> None:
    result = _accepted_result()
    result.pipeline.qa_result.exit_code = "0"

    report = AutonomousCompanyAcceptance().evaluate(result)

    assert not report.passed
    failed = {check.name for check in report.checks if not check.passed}
    assert "qa_exit_code_zero" in failed
