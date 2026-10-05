from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock

from pydantic import BaseModel, Field

from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.models import MissionPlan
from src.company.models.contracts import CompanyMission, CompanyState
from src.company.orchestration.orchestrator import CompanyOrchestrator


class MissionSubmission(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=5000)
    constraints: list[str] = Field(default_factory=list)


class MissionRecord(BaseModel):
    mission: CompanyMission
    status: str
    message: str
    created_at: datetime
    updated_at: datetime
    plan: MissionPlan


class CompanyControlCenter:
    """Application-facing control plane for the human company interface."""

    def __init__(self, orchestrator: CompanyOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator or CompanyOrchestrator()
        self._mission_controller = MissionController(self._orchestrator)
        self._missions: dict[str, MissionRecord] = {}
        self._lock = Lock()

    @property
    def state(self) -> CompanyState:
        return self._orchestrator.state.model_copy(deep=True)

    def events(self):
        return self._orchestrator.events.list_events()

    def missions(self) -> list[MissionRecord]:
        with self._lock:
            return sorted(self._missions.values(), key=lambda item: item.created_at, reverse=True)

    def submit_mission(self, submission: MissionSubmission) -> MissionRecord:
        with self._lock:
            if self._orchestrator.state.status.value == "running":
                raise RuntimeError("Company is already running a mission")
            mission = CompanyMission(
                name=submission.name.strip(),
                objective=submission.objective.strip(),
                constraints=[item.strip() for item in submission.constraints if item.strip()],
            )
            plan, result = self._mission_controller.start(mission)
            now = datetime.now(UTC)
            record = MissionRecord(
                mission=mission,
                status=result.state.status.value,
                message=result.message,
                created_at=now,
                updated_at=now,
                plan=plan,
            )
            self._missions[mission.id] = record
            return record

    def stop(self) -> CompanyState:
        self._orchestrator.stop()
        self._sync_latest()
        return self.state

    def block(self, reason: str) -> CompanyState:
        self._orchestrator.block(reason)
        self._sync_latest()
        return self.state

    def _sync_latest(self) -> None:
        with self._lock:
            if not self._missions:
                return
            latest = max(self._missions.values(), key=lambda item: item.updated_at)
            self._missions[latest.mission.id] = latest.model_copy(
                update={
                    "status": self._orchestrator.state.status.value,
                    "message": self._orchestrator.state.last_decision.value
                    if self._orchestrator.state.last_decision
                    else "Company state updated",
                    "updated_at": datetime.now(UTC),
                }
            )


control_center = CompanyControlCenter()
