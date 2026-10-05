from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from threading import Lock

from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentResult
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.models import MissionPlan
from src.company.mission_jobs import MissionJob, MissionJobStatus, transition_job
from src.company.models.contracts import CompanyMission, CompanyState
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.persistence import MissionJobStore, ProjectStore
from src.company.project_factory import ProjectFactory
from src.runtime.providers.ollama import OllamaProvider
from src.runtime.service import AIRuntime


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
        self._execution_pipeline = MissionExecutionPipeline(
            self._orchestrator,
            AgentExecutor(AIRuntime(OllamaProvider())),
            AgentRegistry(),
        )
        self._missions: dict[str, MissionRecord] = {}
        self._jobs: dict[str, MissionJob] = {}
        self._store = ProjectStore()
        self._job_store = MissionJobStore()
        try:
            for job in self._job_store.list_all():
                self._jobs[job.id] = job
                self._missions[job.id] = MissionRecord(
                    mission=job.mission,
                    status=job.status.value,
                    message=job.message,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    plan=job.plan,
                )
        except SQLAlchemyError:
            pass
        self._factory = ProjectFactory(
            self._orchestrator,
            self._mission_controller,
            self._execution_pipeline,
            store=self._store,
            job_store=self._job_store,
        )
        try:
            self._factory.restore()
        except SQLAlchemyError:
            pass
        self._factory_task: asyncio.Task[None] | None = None
        self._lock = Lock()

    @property
    def state(self) -> CompanyState:
        return self._orchestrator.state.model_copy(deep=True)

    def events(self):
        return self._orchestrator.events.list_events()

    def mission_plan(self, mission_id: str) -> MissionPlan | None:
        return self._mission_controller.get_plan(mission_id)

    def missions(self) -> list[MissionRecord]:
        with self._lock:
            return sorted(
                self._missions.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )

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
            job = MissionJob(
                id=mission.id,
                mission=mission,
                plan=plan,
                status=MissionJobStatus.RUNNING,
                message=result.message,
            )
            self._jobs[mission.id] = job
            try:
                self._job_store.save(job)
            except SQLAlchemyError:
                pass
            return record

    async def run_factory(self, max_projects: int | None = None, max_stages: int | None = None, max_retries: int = 2) -> None:
        if self._factory_task is not None and not self._factory_task.done():
            raise RuntimeError("Factory is already running")
        async def runner() -> None:
            await self._factory.run(
                max_projects=max_projects,
                max_stages=max_stages,
                max_retries=max_retries,
            )
        self._factory_task = asyncio.create_task(runner())

    def factory_running(self) -> bool:
        return self._factory_task is not None and not self._factory_task.done()

    def enqueue_factory_mission(self, mission_id: str) -> None:
        record = self._get_mission(mission_id)
        self._factory.enqueue(record.mission)
        job = self._job_store.get(mission_id)
        if job is not None:
            self._jobs[mission_id] = job
            self._sync_mission_from_job(job)

    def mission_job(self, mission_id: str) -> MissionJob | None:
        try:
            job = self._job_store.get(mission_id)
        except SQLAlchemyError:
            job = self._jobs.get(mission_id)
        if job is not None:
            self._jobs[mission_id] = job
        return job

    def mission_jobs(self) -> list[MissionJob]:
        try:
            jobs = self._job_store.list_all()
        except SQLAlchemyError:
            jobs = sorted(
                self._jobs.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
        for job in jobs:
            self._jobs[job.id] = job
            self._sync_mission_from_job(job)
        return jobs

    async def execute_next_stage(self, mission_id: str) -> AgentResult:
        record = self._get_mission(mission_id)
        result = await self._execution_pipeline.execute_next(record.mission, record.plan)
        self._update_record(record, result)
        return result

    async def execute_mission(
        self,
        mission_id: str,
        max_stages: int | None = None,
    ) -> list[AgentResult]:
        record = self._get_mission(mission_id)
        results = await self._execution_pipeline.execute_mission(
            record.mission,
            record.plan,
            max_stages=max_stages,
        )
        message = (
            f"Executed {len(results)} stage(s)"
            if results
            else "No stages executed"
        )
        if results and not results[-1].success:
            message = results[-1].error or "Mission execution failed"
        self._update_record(record, results[-1] if results else None, message=message)
        return results

    def stop(self) -> CompanyState:
        self._orchestrator.stop()
        self._sync_latest()
        return self.state

    def block(self, reason: str) -> CompanyState:
        self._orchestrator.block(reason)
        self._sync_latest()
        return self.state

    def _get_mission(self, mission_id: str) -> MissionRecord:
        with self._lock:
            record = self._missions.get(mission_id)
        if record is None:
            raise KeyError(f"Mission '{mission_id}' not found")
        return record

    def _sync_mission_from_job(self, job: MissionJob) -> None:
        with self._lock:
            record = self._missions.get(job.id)
            if record is not None:
                self._missions[job.id] = record.model_copy(
                    update={
                        "status": job.status.value,
                        "message": job.message,
                        "updated_at": job.updated_at,
                        "plan": job.plan,
                    }
                )

    def _update_record(
        self,
        record: MissionRecord,
        result: AgentResult | None,
        message: str | None = None,
    ) -> None:
        with self._lock:
            self._missions[record.mission.id] = record.model_copy(
                update={
                    "status": self._orchestrator.state.status.value,
                    "message": (
                        message
                        or (result.output if result and result.success else result.error if result else "Execution stopped")
                    ),
                    "updated_at": datetime.now(UTC),
                    "plan": record.plan,
                }
            )

    def _sync_latest(self) -> None:
        with self._lock:
            if not self._missions:
                return
            latest = max(self._missions.values(), key=lambda item: item.updated_at)
            self._missions[latest.mission.id] = latest.model_copy(
                update={
                    "status": self._orchestrator.state.status.value,
                    "message": (
                        self._orchestrator.state.last_decision.value
                        if self._orchestrator.state.last_decision
                        else "Company state updated"
                    ),
                    "updated_at": datetime.now(UTC),
                }
            )


control_center = CompanyControlCenter()
