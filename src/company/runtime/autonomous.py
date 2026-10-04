from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from src.company.runtime.pipeline_bridge import (
    RuntimePipelineBridge,
    RuntimePipelineRequest,
)
from src.company.runtime.run_registry import RuntimeRunRegistry, RuntimeRunStatus


@dataclass(slots=True, frozen=True)
class RuntimeRunResult:
    run_id: str
    submitted: bool
    result: Any
    processed: int
    failed: int


class AutonomousRuntime:
    def __init__(self, pipeline: Any, *, dispatcher=None) -> None:
        self.bridge = RuntimePipelineBridge(pipeline, dispatcher=dispatcher)
        self.registry = RuntimeRunRegistry()
        self._futures: dict[str, asyncio.Future[Any]] = {}

    async def start(self) -> None:
        await self.bridge.start()

    async def submit(
        self,
        *,
        project_request: Any,
        mission: Any,
        tasks: list[Any],
        qa_request: Any,
        files: dict[str, str],
        agent_executor: Any = None,
        repair_agent_executor: Any = None,
        github_repository: Any = None,
        pull_request_head: str | None = None,
    ) -> str:
        run = self.registry.create()

        request = RuntimePipelineRequest(
            project_request=project_request,
            mission=mission,
            tasks=tasks,
            qa_request=qa_request,
            files=files,
            agent_executor=agent_executor,
            repair_agent_executor=repair_agent_executor,
            github_repository=github_repository,
            pull_request_head=pull_request_head,
        )

        future = await self.bridge.submit(request)

        self._futures[run.run_id] = future
        self.registry.mark_running(run.run_id)

        def finalize(done: asyncio.Future[Any]) -> None:
            self._futures.pop(run.run_id, None)

            if done.cancelled():
                self.registry.mark_cancelled(run.run_id)
                return

            error = done.exception()

            if error is not None:
                self.registry.mark_failed(run.run_id, error)
                return

            self.registry.mark_completed(run.run_id, done.result())

        future.add_done_callback(finalize)

        return run.run_id

    async def wait_run(self, run_id: str) -> Any:
        future = self._futures.get(run_id)

        if future is not None:
            return await future

        run = self.registry.get(run_id)

        if run is None:
            raise KeyError(run_id)

        if run.status is RuntimeRunStatus.COMPLETED:
            return run.result

        if run.status is RuntimeRunStatus.FAILED and run.error is not None:
            raise run.error

        if run.status is RuntimeRunStatus.CANCELLED:
            raise asyncio.CancelledError

        raise KeyError(f"Unknown or unavailable runtime run: {run_id}")

    async def cancel_run(self, run_id: str) -> bool:
        future = self._futures.get(run_id)

        if future is None:
            run = self.registry.get(run_id)
            return run.status is RuntimeRunStatus.CANCELLED

        if future.done():
            return False

        future.cancel()
        return True

    async def run(self, **kwargs: Any) -> RuntimeRunResult:
        run_id = await self.submit(**kwargs)
        result = await self.wait_run(run_id)

        await self.bridge.wait()
        state = await self.bridge.state()

        return RuntimeRunResult(
            run_id=run_id,
            submitted=True,
            result=result,
            processed=state.processed,
            failed=state.failed,
        )

    async def stop(self) -> None:
        await self.bridge.stop()

    async def state(self):
        return await self.bridge.state()
