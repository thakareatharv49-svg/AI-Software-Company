from company.production import CloudDeploymentService, HealthSignal, IncidentService, InfrastructureService, ObservabilityService, RecoveryService

def test_infrastructure_plan():
    assert InfrastructureService().plan("api", "prod", ["cpu"]).environment == "prod"

def test_deployment_request():
    assert CloudDeploymentService().deploy("api", "prod", "v1").status == "requested"

def test_health_evaluation():
    result = ObservabilityService().evaluate([HealthSignal("api", "latency", 40, 50)])
    assert result["healthy"] is False

def test_event_creation():
    assert IncidentService().create("api", "high", "threshold").status == "open"

def test_recovery_plan():
    assert RecoveryService().rollback("api", "v0").action == "rollback"
