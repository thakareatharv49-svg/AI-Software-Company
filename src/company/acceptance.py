from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from company.autonomous_project import AutonomousProjectResult


class AcceptanceStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class AcceptanceCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CompanyAcceptanceReport:
    status: AcceptanceStatus
    checks: tuple[AcceptanceCheck, ...]

    @property
    def passed(self) -> bool:
        return self.status == AcceptanceStatus.PASSED


class AutonomousCompanyAcceptance:
    """Formal M37 acceptance gate for a single human mission."""

    REQUIRED_STAGES = (
        "ai_ceo",
        "research",
        "research_handoff",
        "product_definition",
        "architecture",
        "engineering_qa_security_github",
        "deployment",
        "monitoring",
        "learning",
        "dashboard",
    )

    @staticmethod
    def _status_value(value: Any) -> str:
        """Read enum-backed and plain-string statuses consistently."""
        raw = getattr(value, "value", value)
        return str(raw).strip().lower()

    @staticmethod
    def _requires_browser_preview(objective: str) -> bool:
        """Require a browser entry point for app-like missions, not CLI/library work."""
        text = objective.casefold()
        non_browser_terms = (
            "command-line", "command line", "cli tool", "terminal utility",
            "api-only", "api only", "backend-only", "backend only",
            "python library", "javascript library", "native mobile app",
            "desktop app",
        )
        if any(term in f" {text} " for term in non_browser_terms):
            return False
        browser_terms = (
            "web app", "web application", "website", "web site", "browser",
            " app", " apps", "tracker", "planner", "dashboard", "storefront",
            "e-commerce", " ecommerce", "management system", "portfolio",
            "landing page",
        )
        return any(term in f" {text} " for term in browser_terms)

    def evaluate(self, result: AutonomousProjectResult) -> CompanyAcceptanceReport:
        checks: list[AcceptanceCheck] = []
        stage_map = {stage.name: stage for stage in result.stages}

        mission_status = self._status_value(result.ceo.mission.status)
        checks.append(
            AcceptanceCheck(
                "mission_approved",
                not result.ceo.decision.requires_human and mission_status == "approved",
                "Mission was approved without human escalation.",
            )
        )

        for name in self.REQUIRED_STAGES:
            stage = stage_map.get(name)
            stage_completed = (
                stage is not None
                and self._status_value(stage.status) == "completed"
            )
            checks.append(
                AcceptanceCheck(
                    name,
                    stage_completed,
                    "Required autonomous stage completed."
                    if stage_completed
                    else "Required autonomous stage did not complete.",
                )
            )

        project = result.pipeline.project
        checks.append(
            AcceptanceCheck(
                "real_project",
                bool(project.id and project.name),
                "Project identity is present.",
            )
        )
        qa_result = result.pipeline.qa_result
        qa_status_passed = self._status_value(
            getattr(qa_result, "status", None)
        ) == "passed"
        checks.append(
            AcceptanceCheck(
                "qa_passed",
                qa_status_passed,
                "QA runner reports passed."
                if qa_status_passed
                else "QA runner did not report passed.",
            )
        )
        qa_exit_code = getattr(qa_result, "exit_code", None)
        qa_exit_code_passed = (
            isinstance(qa_exit_code, int)
            and not isinstance(qa_exit_code, bool)
            and qa_exit_code == 0
        )
        checks.append(
            AcceptanceCheck(
                "qa_exit_code_zero",
                qa_exit_code_passed,
                "QA process exited successfully."
                if qa_exit_code_passed
                else f"QA process exit code must be 0; received {qa_exit_code!r}.",
            )
        )

        # The command ledger is created by the execution pipeline and records
        # each configured/generated suite that actually ran. Missing or malformed
        # provenance must never be mistaken for a completed verification run.
        qa_checks = getattr(result.pipeline, "qa_checks", None)
        ledger_is_valid = isinstance(qa_checks, list) and bool(qa_checks)
        ledger_failures: list[str] = []
        if ledger_is_valid:
            for index, check in enumerate(qa_checks):
                if not isinstance(check, dict):
                    ledger_failures.append(f"check {index + 1} has an invalid record")
                    continue
                status = self._status_value(check.get("status"))
                exit_code = check.get("exit_code")
                if status != "passed":
                    ledger_failures.append(
                        f"{check.get('kind', f'check {index + 1}')} status={status or 'missing'}"
                    )
                if not (
                    isinstance(exit_code, int)
                    and not isinstance(exit_code, bool)
                    and exit_code == 0
                ):
                    ledger_failures.append(
                        f"{check.get('kind', f'check {index + 1}')} exit_code={exit_code!r}"
                    )
        ledger_passed = ledger_is_valid and not ledger_failures
        checks.append(
            AcceptanceCheck(
                "qa_evidence_complete",
                ledger_passed,
                "Every recorded QA command has a passing status and zero exit code."
                if ledger_passed
                else (
                    "QA command evidence is missing, malformed, or failing: "
                    + ("; ".join(ledger_failures[:8]) if ledger_failures else "no QA command ledger")
                ),
            )
        )
        checks.append(
            AcceptanceCheck(
                "security_approved",
                self._status_value(result.pipeline.review_result.status) == "approved",
                "Security/code review gate approved.",
            )
        )
        objective = str(getattr(result.ceo.mission, "objective", ""))
        # The approved objective is sometimes terse (for example, "build this")
        # while the product name carries the app category. Use both signals so a
        # vague objective cannot bypass the browser-preview delivery requirement.
        mission_text = f"{project.name} {objective}"
        if self._requires_browser_preview(mission_text):
            preview_available = bool(
                getattr(result.pipeline, "browser_preview", False)
            )
            checks.append(
                AcceptanceCheck(
                    "browser_preview_available",
                    preview_available,
                    "Browser app has a root index.html entry point."
                    if preview_available
                    else (
                        "App-like mission has no browser preview; generated "
                        "files must include a root index.html."
                    ),
                )
            )
            browser_acceptance = getattr(
                result.pipeline, "browser_acceptance", None
            )
            browser_status = self._status_value(
                browser_acceptance.get("status")
                if isinstance(browser_acceptance, dict)
                else None
            )
            browser_passed = preview_available and browser_status == "passed"
            checks.append(
                AcceptanceCheck(
                    "browser_acceptance_passed",
                    browser_passed,
                    "Browser acceptance passed for the generated web product."
                    if browser_passed
                    else (
                        "Browser product requires recorded passing browser acceptance; "
                        f"received {browser_status or 'missing'}."
                    ),
                )
            )
        checks.append(
            AcceptanceCheck(
                "deployment_completed",
                self._status_value(result.deployment.status) == "completed",
                "Deployment completed.",
            )
        )
        checks.append(
            AcceptanceCheck(
                "monitoring_completed",
                self._status_value(result.monitoring.status) == "completed",
                "Monitoring completed.",
            )
        )
        checks.append(
            AcceptanceCheck(
                "learning_recorded",
                bool(result.learning.signals),
                "Learning produced at least one signal.",
            )
        )

        status = (
            AcceptanceStatus.PASSED
            if all(check.passed for check in checks)
            else AcceptanceStatus.FAILED
        )
        return CompanyAcceptanceReport(status, tuple(checks))
