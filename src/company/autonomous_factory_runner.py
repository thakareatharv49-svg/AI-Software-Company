from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from src.company.autonomous_project import (
    AutonomousProjectRequest,
    AutonomousProjectResult,
    AutonomousProjectRunner,
)
from src.company.models.contracts import CompanyMission
from src.company.mission_controller.models import MissionPlan


class AutonomousProjectRunnerProtocol(Protocol):
    async def run(self, request: AutonomousProjectRequest) -> AutonomousProjectResult: ...


AutonomousProjectRequestBuilder = Callable[
    [CompanyMission, MissionPlan],
    AutonomousProjectRequest,
]


class FactoryAutonomousRunner:
    """Adapter that connects a factory mission to the real M36 runner."""

    def __init__(
        self,
        runner: AutonomousProjectRunner,
        request_builder: AutonomousProjectRequestBuilder,
    ) -> None:
        self.runner = runner
        self.request_builder = request_builder

    async def run(
        self,
        mission: CompanyMission,
        plan: MissionPlan,
    ) -> AutonomousProjectResult:
        request = self.request_builder(mission, plan)
        return await self.runner.run(request)
