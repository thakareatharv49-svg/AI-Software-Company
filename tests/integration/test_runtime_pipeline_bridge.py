import pytest

from src.company.runtime.pipeline_bridge import (
    RuntimePipelineBridge,
    RuntimePipelineRequest,
)


class FakePipeline:
    async def run_end_to_end(self, **kwargs):
        return {"ok": True}


class FailingPipeline:
    async def run_end_to_end(self, **kwargs):
        raise RuntimeError("bridge failure")


def build_request() -> RuntimePipelineRequest:
    return RuntimePipelineRequest(
        project_request="project",
        mission="mission",
        tasks=["task"],
        qa_request="qa",
        files={"main.py": "pass"},
    )


@pytest.mark.asyncio
async def test_bridge_submit_returns_pipeline_result_future():
    bridge = RuntimePipelineBridge(FakePipeline())

    await bridge.start()

    future = await bridge.submit(build_request())

    assert await future == {"ok": True}

    await bridge.wait()
    state = await bridge.state()

    assert state.processed == 1
    assert state.failed == 0

    await bridge.stop()


@pytest.mark.asyncio
async def test_bridge_submit_future_propagates_pipeline_failure():
    bridge = RuntimePipelineBridge(FailingPipeline())

    await bridge.start()

    future = await bridge.submit(build_request())

    with pytest.raises(RuntimeError, match="bridge failure"):
        await future

    await bridge.wait()
    state = await bridge.state()

    assert state.processed == 0
    assert state.failed == 1

    await bridge.stop()
