def test_loop_modules_exist():
    from src.company.loop import (
    ConcurrentProjectRunner,
    OpportunityDiscovery,
    ProjectLifecycle,
    SelfHealingService,
)
    assert ProjectLifecycle
    assert ConcurrentProjectRunner
    assert SelfHealingService
    assert OpportunityDiscovery
