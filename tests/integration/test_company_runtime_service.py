import pytest

from src.company.runtime.config import RuntimeConfig
from src.company.runtime.service import CompanyRuntimeService


class FakePipeline:
    def __init__(self) -> None:
        self.calls = []

    async def run_end_to_end(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "status": "completed",
            "project_id": f"project-{len(self.calls)}",
        }


@pytest.mark.asyncio
async def test_company_runtime_service_controls_lifecycle():
    pipeline = FakePipeline()

    config = RuntimeConfig(
        environment="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        max_concurrent_runs=2,
        shutdown_timeout_seconds=5.0,
    )

    service = CompanyRuntimeService(
        pipeline,
        config=config,
    )

    state = await service.state()
    assert state.running is False

    await service.start()

    state = await service.state()
    assert state.running is True
    assert state.worker_count == 2

    await service.stop()

    state = await service.state()
    assert state.running is False


@pytest.mark.asyncio
async def test_company_runtime_service_executes_real_pipeline():
    pipeline = FakePipeline()

    config = RuntimeConfig(
        environment="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        max_concurrent_runs=1,
        shutdown_timeout_seconds=5.0,
    )

    service = CompanyRuntimeService(
        pipeline,
        config=config,
    )

    await service.start()

    result = await service.run(
        project_request="project",
        mission="mission",
        tasks=["task"],
        qa_request="qa",
        files={"main.py": "pass"},
    )

    assert result.result == {
        "status": "completed",
        "project_id": "project-1",
    }
    assert result.processed == 1
    assert result.failed == 0
    assert len(pipeline.calls) == 1

    await service.stop()


@pytest.mark.asyncio
async def test_company_runtime_service_rejects_run_before_start():
    service = CompanyRuntimeService(FakePipeline())

    with pytest.raises(
        RuntimeError,
        match="Company runtime service is not running",
    ):
        await service.run(
            project_request="project",
            mission="mission",
            tasks=[],
            qa_request="qa",
            files={},
        )


@pytest.mark.asyncio
async def test_company_runtime_service_start_is_idempotent():
    service = CompanyRuntimeService(
        FakePipeline(),
        config=RuntimeConfig(
            environment="test",
            host="127.0.0.1",
            port=8000,
            debug=False,
            max_concurrent_runs=1,
            shutdown_timeout_seconds=5.0,
        ),
    )

    await service.start()
    await service.start()

    state = await service.state()
    assert state.running is True

    await service.stop()
    await service.stop()

    state = await service.state()
    assert state.running is False


def test_company_runtime_service_requires_pipeline():
    with pytest.raises(ValueError, match="pipeline is required"):
        CompanyRuntimeService(None)
