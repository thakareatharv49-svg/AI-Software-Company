import pytest

from src.company.runtime.autonomous import AutonomousRuntime


class FakePipeline:
    def __init__(self) -> None:
        self.calls = []

    async def run_end_to_end(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "completed", "project_id": "project-1"}


class FailingPipeline:
    async def run_end_to_end(self, **kwargs):
        raise RuntimeError("pipeline failure")


@pytest.mark.asyncio
async def test_autonomous_runtime_returns_real_pipeline_result():
    pipeline = FakePipeline()
    runtime = AutonomousRuntime(pipeline)

    await runtime.start()

    result = await runtime.run(
        project_request="project-request",
        mission="mission",
        tasks=["task"],
        qa_request="qa",
        files={"app.py": "print('ok')"},
    )

    assert result.result == {
        "status": "completed",
        "project_id": "project-1",
    }
    assert result.processed == 1
    assert result.failed == 0
    assert len(pipeline.calls) == 1

    await runtime.stop()


@pytest.mark.asyncio
async def test_autonomous_runtime_propagates_pipeline_failure():
    runtime = AutonomousRuntime(FailingPipeline())

    await runtime.start()

    with pytest.raises(RuntimeError, match="pipeline failure"):
        await runtime.run(
            project_request="project-request",
            mission="mission",
            tasks=["task"],
            qa_request="qa",
            files={},
        )

    state = await runtime.state()

    assert state.processed == 0
    assert state.failed == 1

    await runtime.stop()


@pytest.mark.asyncio
async def test_autonomous_runtime_forwards_all_pipeline_arguments():
    pipeline = FakePipeline()
    runtime = AutonomousRuntime(pipeline)

    await runtime.start()

    agent_executor = object()
    repair_agent_executor = object()
    github_repository = object()

    await runtime.run(
        project_request="project",
        mission="mission",
        tasks=["task-1", "task-2"],
        qa_request="qa",
        files={"main.py": "pass"},
        agent_executor=agent_executor,
        repair_agent_executor=repair_agent_executor,
        github_repository=github_repository,
        pull_request_head="feature/test",
    )

    call = pipeline.calls[0]

    assert call["project_request"] == "project"
    assert call["mission"] == "mission"
    assert call["tasks"] == ["task-1", "task-2"]
    assert call["qa_request"] == "qa"
    assert call["files"] == {"main.py": "pass"}
    assert call["agent_executor"] is agent_executor
    assert call["repair_agent_executor"] is repair_agent_executor
    assert call["github_repository"] is github_repository
    assert call["pull_request_head"] == "feature/test"

    await runtime.stop()
