from src.company.gates.quality import GateDecision, ProductionQualityGate


def require_deployment_gate(
    *,
    qa_passed: bool,
    security_approved: bool,
    github_ready: bool = True,
) -> GateDecision:
    return ProductionQualityGate().evaluate(
        qa_passed=qa_passed,
        security_approved=security_approved,
        github_ready=github_ready,
        deployment_ready=True,
    )
