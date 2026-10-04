from dataclasses import dataclass
from typing import Any

from company.runtime.dispatcher import RuntimeDispatcher


@dataclass(slots=True, frozen=True)
class RuntimePipelineRequest:
    project_request: Any
    mission: Any
    tasks: list[Any]
    qa_request: Any
    files: dict[str, str]
    agent_executor: Any = None
    repair_agent_executor: Any = None
    github_repository: Any = None
    pull_request_head: str | None = None


class RuntimePipelineBridge:
    def __init__(
        self,
        pipeline: Any,
        *,
        dispatcher: RuntimeDispatcher | None = None,
    ) -> None:
        if pipeline is None:
            raise ValueError("pipeline is required")

        if not callable(getattr(pipeline, "run_end_to_end", None)):
            raise TypeError("pipeline must provide run_end_to_end")

        self.pipeline = pipeline
        self.dispatcher = dispatcher or RuntimeDispatcher()

    async def start(self) -> None:
        await self.dispatcher.start()

    async def submit(self, request: RuntimePipelineRequest) -> None:
        async def operation() -> Any:
            return await self.pipeline.run_end_to_end(
                project_request=request.project_request,
                mission=request.mission,
                tasks=request.tasks,
                qa_request=request.qa_request,
                files=request.files,
                agent_executor=request.agent_executor,
                repair_agent_executor=request.repair_agent_executor,
                github_repository=request.github_repository,
                pull_request_head=request.pull_request_head,
            )

        await self.dispatcher.submit(operation)

    async def wait(self) -> None:
        await self.dispatcher.wait()

    async def stop(self) -> None:
        await self.dispatcher.stop()

    async def state(self):
        return await self.dispatcher.state()
