from unittest.mock import AsyncMock

import pytest

from company.runtime.autonomous import AutonomousRuntime


class FakePipeline:
    def __init__(self) -> None:
        self.run_end_to_end = AsyncMock(return_value="completed")


@pytest.mark.asyncio
async def test_autonomous_runtime_executes_company_pipeline():
    pipeline = FakePipeline()
    runtime = AutonomousRuntime(pipeline)

    await runtime.start()

    result = await runtime.run(
        project_request="project",
        mission="mission",
        tasks=["task"],
        qa_request="qa",
        files={"main.py": "print('ok')"},
    )

    assert result.submitted is True
    assert result.processed == 1
    assert result.failed == 0

    pipeline.run_end_to_end.assert_awaited_once()

    await runtime.stop()


@pytest.mark.asyncio
async def test_autonomous_runtime_tracks_pipeline_failure():
    class FailingPipeline:
        async def run_end_to_end(self, **kwargs):
            raise RuntimeError("execution failed")

    runtime = AutonomousRuntime(FailingPipeline())

    await runtime.start()

    result = await runtime.run(
        project_request="project",
        mission="mission",
        tasks=[],
        qa_request="qa",
        files={},
    )

    assert result.submitted is True
    assert result.processed == 0
    assert result.failed == 1

    await runtime.stop()


@pytest.mark.asyncio
async def test_autonomous_runtime_state():
    pipeline = FakePipeline()
    runtime = AutonomousRuntime(pipeline)

    await runtime.start()

    state = await runtime.state()

    assert state.running is True
    assert state.processed == 0
    assert state.failed == 0

    await runtime.stop()

    state = await runtime.state()
    assert state.running is False


@pytest.mark.asyncio
async def test_autonomous_runtime_supports_full_pipeline_arguments():
    pipeline = FakePipeline()
    runtime = AutonomousRuntime(pipeline)

    await runtime.start()

    await runtime.run(
        project_request="project",
        mission="mission",
        tasks=["task"],
        qa_request="qa",
        files={"main.py": "pass"},
        agent_executor="agent",
        repair_agent_executor="repair",
        github_repository="github",
        pull_request_head="feature/test",
    )

    call = pipeline.run_end_to_end.await_args.kwargs

    assert call["agent_executor"] == "agent"
    assert call["repair_agent_executor"] == "repair"
    assert call["github_repository"] == "github"
    assert call["pull_request_head"] == "feature/test"

    await runtime.stop()
