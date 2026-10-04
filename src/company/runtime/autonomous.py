from dataclasses import dataclass
from typing import Any

from company.runtime.pipeline_bridge import RuntimePipelineBridge, RuntimePipelineRequest


@dataclass(slots=True, frozen=True)
class RuntimeRunResult:
    submitted: bool
    processed: int
    failed: int


class AutonomousRuntime:
    def __init__(
        self,
        pipeline: Any,
        *,
        dispatcher=None,
    ) -> None:
        self.bridge = RuntimePipelineBridge(
            pipeline,
            dispatcher=dispatcher,
        )

    async def start(self) -> None:
        await self.bridge.start()

    async def run(
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
    ) -> RuntimeRunResult:
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

        await self.bridge.submit(request)
        await self.bridge.wait()

        state = await self.bridge.state()

        return RuntimeRunResult(
            submitted=True,
            processed=state.processed,
            failed=state.failed,
        )

    async def stop(self) -> None:
        await self.bridge.stop()

    async def state(self):
        return await self.bridge.state()
