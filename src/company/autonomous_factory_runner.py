from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from src.company.autonomous_project import (
    AutonomousProjectRequest,
    AutonomousProjectResult,
    AutonomousProjectRunner,
)
from src.company.mission_controller.models import MissionPlan
from src.company.models.contracts import CompanyMission
from src.company.workspace import ProjectExecutionService


class AutonomousProjectRunnerProtocol(Protocol):
    async def run(self, request: AutonomousProjectRequest) -> AutonomousProjectResult: ...


AutonomousProjectRequestBuilder = Callable[
    [CompanyMission, MissionPlan],
    AutonomousProjectRequest | Awaitable[AutonomousProjectRequest],
]


class FactoryAutonomousRunner:
    """Adapter that connects a factory mission to the real M36 runner."""

    def __init__(
        self,
        runner: AutonomousProjectRunner,
        request_builder: AutonomousProjectRequestBuilder,
        workspace_service: ProjectExecutionService | None = None,
    ) -> None:
        self.runner = runner
        self.request_builder = request_builder
        self.workspace_service = workspace_service or ProjectExecutionService(
            Path(__file__).resolve().parents[2] / "generated-products"
        )

    async def run(
        self,
        mission: CompanyMission,
        plan: MissionPlan,
    ) -> AutonomousProjectResult:
        request = self.request_builder(mission, plan)
        if hasattr(request, "__await__"):
            request = await request
        workspace = self.workspace_service.create_workspace(mission.id)

        try:
            for path, content in request.files.items():
                workspace.write_file(path, content)

            if request.qa_request is not None:
                request = replace(
                    request,
                    qa_request=request.qa_request.model_copy(
                        update={
                            "working_directory": str(workspace.root),
                        }
                    ),
                )
            return await self.runner.run(request)
        finally:
            # Completed workspaces are intentionally retained for the product
            # viewer. Failed attempts are also retained for diagnostics/retry.
            pass
