import asyncio

import pytest

from src.company.loop import (
    CompanyOperatingLoop,
    ConcurrentProjectRunner,
    LifecycleState,
    Opportunity,
    OpportunityDiscovery,
    ProjectLifecycle,
    SelfHealingService,
)


def test_project_lifecycle_guards_transitions():
    lifecycle = ProjectLifecycle("p1")
    lifecycle.transition(LifecycleState.PLANNED)
    lifecycle.transition(LifecycleState.EXECUTING)
    assert lifecycle.state == LifecycleState.EXECUTING
    with pytest.raises(ValueError):
        lifecycle.transition(LifecycleState.RELEASED)


@pytest.mark.asyncio
async def test_concurrent_runner_isolates_project_failures():
    runner = ConcurrentProjectRunner(max_concurrency=2)

    async def ok():
        await asyncio.sleep(0.001)
        return "ok"

    async def bad():
        raise RuntimeError("boom")

    results = await runner.run([("ok", ok), ("bad", bad)])
    assert results[0].success
    assert not results[1].success
    assert results[1].error == "boom"


@pytest.mark.asyncio
async def test_self_healing_retries_and_records_success():
    service = SelfHealingService(max_attempts=2)
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary")

    first = await service.heal("p1", operation)
    second = await service.heal("p1", operation)

    assert not first.success
    assert second.success
    assert calls == 2


def test_discovery_ranks_opportunities():
    discovery = OpportunityDiscovery()
    items = [
        Opportunity("low", "Low", "low value", 5, confidence=1),
        Opportunity("high", "High", "high value", 20, confidence=1),
    ]
    assert discovery.top(items)[0].opportunity_id == "high"


def test_company_loop_selects_with_capacity():
    loop = CompanyOperatingLoop()
    assert loop.select(["a", "b"], 1) == ("a",)
    assert loop.report(["a"], ["a"])["completed"] == ("a",)
