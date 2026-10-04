import asyncio

import pytest

from company.runtime.resource_enforcement import (
    ResourceLimitExceeded,
    RuntimeResourceEnforcer,
    RuntimeResourcePolicy,
)


@pytest.mark.asyncio
async def test_runtime_limit_stops_long_running_task():
    enforcer = RuntimeResourceEnforcer(
        RuntimeResourcePolicy(
            max_runtime_seconds=0.05,
            sample_interval_seconds=0.01,
        )
    )

    async def target():
        await asyncio.sleep(1)

    with pytest.raises(ResourceLimitExceeded, match="runtime limit exceeded"):
        await enforcer.run(target)


@pytest.mark.asyncio
async def test_short_task_completes_within_runtime_limit():
    enforcer = RuntimeResourceEnforcer(
        RuntimeResourcePolicy(
            max_runtime_seconds=1,
            sample_interval_seconds=0.01,
        )
    )

    async def target():
        await asyncio.sleep(0.01)
        return "completed"

    result = await enforcer.run(target)

    assert result == "completed"


@pytest.mark.asyncio
async def test_resource_usage_is_reported():
    enforcer = RuntimeResourceEnforcer(
        RuntimeResourcePolicy(
            max_runtime_seconds=1,
            sample_interval_seconds=0.01,
        )
    )

    started_at = __import__("time").monotonic()

    usage = enforcer.usage(started_at)

    assert usage.elapsed_seconds >= 0
    assert usage.memory_mb > 0
    assert usage.cpu_percent >= 0


def test_invalid_runtime_limit():
    with pytest.raises(ValueError):
        RuntimeResourcePolicy(max_runtime_seconds=0)


def test_invalid_memory_limit():
    with pytest.raises(ValueError):
        RuntimeResourcePolicy(max_memory_mb=0)


def test_invalid_cpu_limit():
    with pytest.raises(ValueError):
        RuntimeResourcePolicy(max_cpu_percent=101)


def test_invalid_sample_interval():
    with pytest.raises(ValueError):
        RuntimeResourcePolicy(sample_interval_seconds=0)
