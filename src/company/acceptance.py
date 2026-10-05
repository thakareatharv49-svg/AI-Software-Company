from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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

    def evaluate(self, result: AutonomousProjectResult) -> CompanyAcceptanceReport:
        checks: list[AcceptanceCheck] = []
        stage_map = {stage.name: stage for stage in result.stages}

        checks.append(
            AcceptanceCheck(
                "mission_approved",
                not result.ceo.decision.requires_human
                and result.ceo.mission.status.value == "approved",
                "Mission was approved without human escalation.",
            )
        )

        for name in self.REQUIRED_STAGES:
            stage = stage_map.get(name)
            checks.append(
                AcceptanceCheck(
                    name,
                    stage is not None and stage.status.value == "completed",
                    "Required autonomous stage completed."
                    if stage is not None and stage.status.value == "completed"
                    else "Required autonomous stage did not complete.",
                )
            )

        checks.append(
            AcceptanceCheck(
                "real_project",
                bool(result.pipeline.project.id and result.pipeline.project.name),
                "Project identity is present.",
            )
        )
        checks.append(
            AcceptanceCheck(
                "qa_passed",
                result.pipeline.qa_result.status.value == "passed",
                "QA gate passed.",
            )
        )
        checks.append(
            AcceptanceCheck(
                "security_approved",
                result.pipeline.review_result.status.value == "approved",
                "Security/code review gate approved.",
            )
        )
        checks.append(
            AcceptanceCheck(
                "deployment_completed",
                result.deployment.status.value == "completed",
                "Deployment completed.",
            )
        )
        checks.append(
            AcceptanceCheck(
                "monitoring_completed",
                result.monitoring.status.value == "completed",
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
