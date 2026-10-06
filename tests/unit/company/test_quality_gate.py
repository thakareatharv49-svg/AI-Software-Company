from src.company.gates import ProductionQualityGate


def test_quality_gate_requires_all_production_checks():
    gate = ProductionQualityGate()

    assert gate.evaluate(
        qa_passed=True,
        security_approved=True,
        github_ready=True,
        deployment_ready=True,
    ).allowed

    blocked = gate.evaluate(
        qa_passed=True,
        security_approved=False,
        github_ready=True,
        deployment_ready=True,
    )

    assert not blocked.allowed
    assert blocked.checks["security"] is False
