import asyncio

import pytest

from company.runtime.process import (
    RuntimeProcessController,
    RuntimeProcessStatus,
)
from company.runtime.resource_enforcement import RuntimeResourcePolicy


@pytest.mark.asyncio
async def test_process_resource_limit_transitions_to_failed():
    async def target():
        await asyncio.sleep(1)

    process = RuntimeProcessController(
        target,
        RuntimeResourcePolicy(
            max_runtime_seconds=0.05,
            sample_interval_seconds=0.01,
        ),
    )

    await process.start()
    await process.wait()

    state = await process.state()

    assert state.status == RuntimeProcessStatus.FAILED
    assert state.return_code == 1
    assert state.error is not None
    assert "runtime limit exceeded" in state.error


@pytest.mark.asyncio
async def test_process_without_resource_limit_keeps_existing_behavior():
    async def target():
        await asyncio.sleep(0.01)

    process = RuntimeProcessController(target)

    await process.start()
    await process.wait()

    state = await process.state()

    assert state.status == RuntimeProcessStatus.STOPPED
    assert state.return_code == 0
    assert state.error is None


@pytest.mark.asyncio
async def test_process_stop_still_works_with_resource_enforcement():
    async def target():
        await asyncio.sleep(10)

    process = RuntimeProcessController(
        target,
        RuntimeResourcePolicy(
            max_runtime_seconds=10,
            sample_interval_seconds=0.01,
        ),
    )

    await process.start()
    await asyncio.sleep(0.02)
    await process.stop()

    state = await process.state()

    assert state.status == RuntimeProcessStatus.STOPPED
    assert state.return_code == -1
