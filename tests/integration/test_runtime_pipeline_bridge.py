from unittest.mock import AsyncMock

import pytest

from company.runtime.pipeline_bridge import (
    RuntimePipelineBridge,
    RuntimePipelineRequest,
)


class FakePipeline:
    def __init__(self) -> None:
        self.run_end_to_end = AsyncMock(return_value="pipeline-result")


@pytest.mark.asyncio
async def test_pipeline_bridge_executes_real_pipeline_contract():
    pipeline = FakePipeline()
    bridge = RuntimePipelineBridge(pipeline, dispatcher=None)

    request = RuntimePipelineRequest(
        project_request="project",
        mission="mission",
        tasks=["task"],
        qa_request="qa",
        files={"app.py": "print('ok')"},
        agent_executor="agent",
        repair_agent_executor="repair",
        github_repository="github",
        pull_request_head="main",
    )

    await bridge.start()
    await bridge.submit(request)
    await bridge.wait()

    pipeline.run_end_to_end.assert_awaited_once_with(
        project_request="project",
        mission="mission",
        tasks=["task"],
        qa_request="qa",
        files={"app.py": "print('ok')"},
        agent_executor="agent",
        repair_agent_executor="repair",
        github_repository="github",
        pull_request_head="main",
    )

    state = await bridge.state()
    assert state.processed == 1
    assert state.failed == 0

    await bridge.stop()


@pytest.mark.asyncio
async def test_pipeline_bridge_preserves_pipeline_failure():
    class FailingPipeline:
        async def run_end_to_end(self, **kwargs):
            raise RuntimeError("pipeline failed")

    bridge = RuntimePipelineBridge(FailingPipeline())

    await bridge.start()

    await bridge.submit(
        RuntimePipelineRequest(
            project_request="project",
            mission="mission",
            tasks=[],
            qa_request="qa",
            files={},
        )
    )

    await bridge.wait()

    state = await bridge.state()
    assert state.failed == 1
    assert state.processed == 0

    await bridge.stop()


def test_pipeline_bridge_rejects_invalid_pipeline():
    with pytest.raises(TypeError, match="run_end_to_end"):
        RuntimePipelineBridge(object())


def test_pipeline_request_defaults_are_optional():
    request = RuntimePipelineRequest(
        project_request="project",
        mission="mission",
        tasks=[],
        qa_request="qa",
        files={},
    )

    assert request.agent_executor is None
    assert request.repair_agent_executor is None
    assert request.github_repository is None
    assert request.pull_request_head is None
