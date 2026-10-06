from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    reason: str
    checks: dict[str, bool]


class ProductionQualityGate:
    """Single release gate shared by QA, security, GitHub and deployment."""

    def evaluate(
        self,
        *,
        qa_passed: bool,
        security_approved: bool,
        github_ready: bool = True,
        deployment_ready: bool = True,
    ) -> GateDecision:
        checks = {
            "qa": qa_passed,
            "security": security_approved,
            "github": github_ready,
            "deployment": deployment_ready,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            return GateDecision(
                False,
                f"Production gate blocked: {', '.join(failed)}",
                checks,
            )
        return GateDecision(True, "All production quality gates passed.", checks)
