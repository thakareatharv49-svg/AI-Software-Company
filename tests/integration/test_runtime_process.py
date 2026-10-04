import asyncio

import pytest

from src.company.runtime.process import (
    RuntimeProcessController,
    RuntimeProcessStatus,
)


@pytest.mark.asyncio
async def test_process_starts_and_stops():
    gate = asyncio.Event()

    async def target():
        await gate.wait()

    process = RuntimeProcessController(target)

    state = await process.state()
    assert state.status is RuntimeProcessStatus.CREATED
    assert state.running is False

    await process.start()

    state = await process.state()
    assert state.status is RuntimeProcessStatus.RUNNING
    assert state.running is True

    await process.stop()

    state = await process.state()
    assert state.status is RuntimeProcessStatus.STOPPED
    assert state.running is False
    assert state.return_code == -1


@pytest.mark.asyncio
async def test_process_completes_successfully():
    async def target():
        await asyncio.sleep(0)

    process = RuntimeProcessController(target)

    await process.start()
    await process.wait()

    state = await process.state()

    assert state.status is RuntimeProcessStatus.STOPPED
    assert state.running is False
    assert state.return_code == 0
    assert state.error is None


@pytest.mark.asyncio
async def test_process_failure_is_recorded():
    async def target():
        raise RuntimeError("boom")

    process = RuntimeProcessController(target)

    await process.start()
    await process.wait()

    state = await process.state()

    assert state.status is RuntimeProcessStatus.FAILED
    assert state.running is False
    assert state.return_code == 1
    assert state.error == "boom"


@pytest.mark.asyncio
async def test_start_is_idempotent():
    gate = asyncio.Event()

    async def target():
        await gate.wait()

    process = RuntimeProcessController(target)

    await process.start()
    await process.start()

    state = await process.state()

    assert state.status is RuntimeProcessStatus.RUNNING
    assert state.running is True

    await process.stop()


@pytest.mark.asyncio
async def test_stop_before_start():
    async def target():
        await asyncio.sleep(0)

    process = RuntimeProcessController(target)

    await process.stop()

    state = await process.state()

    assert state.status is RuntimeProcessStatus.STOPPED
    assert state.running is False


@pytest.mark.asyncio
async def test_wait_before_start_is_safe():
    async def target():
        await asyncio.sleep(0)

    process = RuntimeProcessController(target)

    await process.wait()

    state = await process.state()

    assert state.status is RuntimeProcessStatus.CREATED


def test_invalid_target():
    with pytest.raises(TypeError):
        RuntimeProcessController(None)
