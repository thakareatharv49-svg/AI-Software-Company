from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from src.company.runtime.autonomous import AutonomousRuntime
from src.company.runtime.dispatcher import RuntimeDispatcher
from src.company.runtime.run_registry import RuntimeRunStatus


class FakePipeline:
    def __init__(self) -> None:
        self.calls = 0

    async def run_end_to_end(self, **kwargs):
        self.calls += 1
        await asyncio.sleep(0.01)
        return {
            "call": self.calls,
            "files": kwargs["files"],
        }


@dataclass
class SlowPipeline:
    started: asyncio.Event
    release: asyncio.Event

    async def run_end_to_end(self, **kwargs):
        self.started.set()
        await self.release.wait()
        return {"ok": True}


def request_kwargs():
    return {
        "project_request": SimpleNamespace(),
        "mission": SimpleNamespace(),
        "tasks": [],
        "qa_request": SimpleNamespace(),
        "files": {"main.py": "print('ok')"},
    }


@pytest.mark.asyncio
async def test_autonomous_runtime_returns_pipeline_result():
    runtime = AutonomousRuntime(
        FakePipeline(),
        dispatcher=RuntimeDispatcher(worker_count=1),
    )

    await runtime.start()

    try:
        result = await runtime.run(**request_kwargs())

        assert result.submitted is True
        assert result.result["files"]["main.py"] == "print('ok')"
        assert result.run_id
        assert result.processed == 1
        assert result.failed == 0
        assert (
            runtime.registry.get(result.run_id).status
            is RuntimeRunStatus.COMPLETED
        )
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_autonomous_runtime_supports_concurrent_submissions():
    runtime = AutonomousRuntime(
        FakePipeline(),
        dispatcher=RuntimeDispatcher(worker_count=2),
    )

    await runtime.start()

    try:
        run_ids = await asyncio.gather(
            runtime.submit(**request_kwargs()),
            runtime.submit(**request_kwargs()),
        )

        assert len(set(run_ids)) == 2

        results = await asyncio.gather(
            *(runtime.wait_run(run_id) for run_id in run_ids)
        )

        assert all(
            result["files"]["main.py"] == "print('ok')"
            for result in results
        )

        assert all(
            runtime.registry.get(run_id).status
            is RuntimeRunStatus.COMPLETED
            for run_id in run_ids
        )
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_autonomous_runtime_can_cancel_run():
    started = asyncio.Event()
    release = asyncio.Event()

    runtime = AutonomousRuntime(
        SlowPipeline(started, release),
        dispatcher=RuntimeDispatcher(worker_count=1),
    )

    await runtime.start()

    try:
        run_id = await runtime.submit(**request_kwargs())

        await started.wait()

        assert await runtime.cancel_run(run_id) is True

        with pytest.raises(asyncio.CancelledError):
            await runtime.wait_run(run_id)

        await asyncio.sleep(0)

        assert (
            runtime.registry.get(run_id).status
            is RuntimeRunStatus.CANCELLED
        )

        release.set()
        await runtime.bridge.wait()
    finally:
        release.set()
        await runtime.stop()


@pytest.mark.asyncio
async def test_autonomous_runtime_cancel_completed_run_returns_false():
    runtime = AutonomousRuntime(
        FakePipeline(),
        dispatcher=RuntimeDispatcher(worker_count=1),
    )

    await runtime.start()

    try:
        run_id = await runtime.submit(**request_kwargs())

        await runtime.wait_run(run_id)

        assert await runtime.cancel_run(run_id) is False
        assert (
            runtime.registry.get(run_id).status
            is RuntimeRunStatus.COMPLETED
        )
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_autonomous_runtime_unknown_run_raises():
    runtime = AutonomousRuntime(
        FakePipeline(),
        dispatcher=RuntimeDispatcher(worker_count=1),
    )

    with pytest.raises(KeyError):
        await runtime.wait_run("missing-run")
