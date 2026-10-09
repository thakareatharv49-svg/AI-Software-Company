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
        checks.append(
            AcceptanceCheck(
                "qa_passed",
                self._status_value(result.pipeline.qa_result.status) == "passed",
                "QA gate passed.",
            )
        )
        checks.append(
            AcceptanceCheck(
                "security_approved",
                self._status_value(result.pipeline.review_result.status) == "approved",
                "Security/code review gate approved.",
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
