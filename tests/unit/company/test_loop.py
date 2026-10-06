def test_loop_modules_exist():
    from src.company.loop import ProjectLifecycle, ConcurrentProjectRunner, SelfHealingService, OpportunityDiscovery
    assert ProjectLifecycle
    assert ConcurrentProjectRunner
    assert SelfHealingService
    assert OpportunityDiscovery
