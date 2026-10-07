from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from threading import Lock

from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentResult
from src.agents.registry.registry import AgentRegistry
from src.company.audit import MissionAuditEntry
from src.company.autonomous_factory_runner import FactoryAutonomousRunner
from src.company.autonomous_project import AutonomousProjectRequest, AutonomousProjectRunner
from src.company.ceo.models import Mission as CEOMission
from src.company.execution.pipeline import CompanyExecutionPipeline
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.models import MissionPlan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission, CompanyState
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.persistence import (
    MissionAuditStore,
    MissionJobStore,
    ProjectOutputStore,
    ProjectStore,
)
from src.company.project_factory import ProjectFactory
from src.company.project_generator import OllamaProjectGenerator
from src.company.project_outputs import ProjectOutputManifest
from src.company.research.engine import StaticResearchProvider
from src.manager.models.contracts import Mission as ManagerMission
from src.manager.models.contracts import TaskPlanItem
from src.projects.models.contracts import ProjectCreateRequest
from src.qa.models.contracts import QATestRequest
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
        self._audit_store = MissionAuditStore()
        self._output_store = ProjectOutputStore()
        try:
            self._job_store.recover_running()
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
        self._generator = OllamaProjectGenerator()
        autonomous_runner = AutonomousProjectRunner(
            research_provider=StaticResearchProvider(),
            pipeline=CompanyExecutionPipeline(),
            deployment=lambda pipeline: f"Validated locally: {pipeline.project.name}",
            monitoring=lambda pipeline: f"Monitoring initialized for {pipeline.project.name}",
        )
        self._autonomous_factory_runner = FactoryAutonomousRunner(
            autonomous_runner,
            self._build_autonomous_request,
        )
        self._factory = ProjectFactory(
            self._orchestrator,
            self._mission_controller,
            self._execution_pipeline,
            store=self._store,
            job_store=self._job_store,
            audit_store=self._audit_store,
            output_store=self._output_store,
            autonomous_runner=self._autonomous_factory_runner,
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
                self._audit(
                    mission.id,
                    "MISSION_CREATED",
                    result.message,
                    status=job.status.value,
                )
            except SQLAlchemyError:
                pass
            return record

    async def run_factory(
        self,
        max_projects: int | None = None,
        max_stages: int | None = None,
        max_retries: int = 2,
        mission_id: str | None = None,
    ) -> None:
        if self._factory_task is not None and not self._factory_task.done():
            if mission_id is None:
                raise RuntimeError("Factory is already running")

            job = self.mission_job(mission_id)
            if job is None:
                raise KeyError(mission_id)
            if job.status == MissionJobStatus.RUNNING:
                raise RuntimeError(f"Mission '{mission_id}' is already running in the factory")
            if job.status != MissionJobStatus.QUEUED:
                raise ValueError(
                    f"Mission '{mission_id}' cannot start from '{job.status.value}'"
                )

            # An old factory task can remain alive while the requested mission is
            # still queued, commonly because autonomous execution is hung. An
            # explicit factory-run request must be able to recover that scheduler.
            stale_task = self._factory_task
            stale_task.cancel()
            with suppress(asyncio.CancelledError):
                await stale_task
            self._factory_task = None

            # Cancellation can leave the interrupted project persisted as RUNNING.
            # Recover it and restore durable factory work before starting again.
            try:
                self._job_store.recover_running()
                for recovered in self._job_store.list_all():
                    self._jobs[recovered.id] = recovered
                    self._sync_mission_from_job(recovered)
                self._factory.restore()
            except SQLAlchemyError:
                pass

        async def runner() -> None:
            try:
                # The factory performs synchronous database/file operations while
                # orchestrating async work. Run the whole factory loop outside
                # FastAPI's event-loop thread so long-running project execution
                # can never block health/status/job HTTP requests.
                def run_factory_sync() -> None:
                    asyncio.run(
                        self._factory.run(
                            max_projects=max_projects,
                            max_stages=max_stages,
                            max_retries=max_retries,
                        )
                    )

                await asyncio.to_thread(run_factory_sync)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Never let an unobserved background exception leave a mission
                # permanently stuck in RUNNING/QUEUED with no durable explanation.
                if mission_id is not None:
                    job = self._job_store.get(mission_id)
                    if job is not None and job.status in {
                        MissionJobStatus.QUEUED,
                        MissionJobStatus.RUNNING,
                    }:
                        from src.company.mission_jobs import transition_job

                        failed = transition_job(
                            job,
                            MissionJobStatus.FAILED,
                            f"Factory execution failed: {exc}",
                        )
                        self._job_store.save(failed)
                        self._jobs[mission_id] = failed
                        self._sync_mission_from_job(failed)
                        self._audit(
                            mission_id,
                            "FACTORY_EXECUTION_FAILED",
                            failed.message,
                            status=failed.status.value,
                            metadata={"error": str(exc)},
                        )
                raise

        # Start the factory in the background and return control to the HTTP
        # request immediately. The task owns all long-running autonomous work;
        # its failures are persisted by runner() so callers can inspect /job
        # instead of waiting for the factory to finish.
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

    def cancel_mission(self, mission_id: str) -> MissionJob:
        try:
            job = self._factory.cancel(mission_id)
        except SQLAlchemyError:
            raise
        self._jobs[mission_id] = job
        self._sync_mission_from_job(job)
        try:
            self._audit(mission_id, "MISSION_CANCELLED", job.message, status=job.status.value)
        except SQLAlchemyError:
            pass
        return job

    def retry_mission(self, mission_id: str) -> MissionJob:
        job = self._factory.retry(mission_id)
        self._jobs[mission_id] = job
        self._sync_mission_from_job(job)
        try:
            self._audit(mission_id, "MISSION_REQUEUED", job.message, status=job.status.value)
        except SQLAlchemyError:
            pass
        return job

    def project_outputs(self, mission_id: str) -> list[ProjectOutputManifest]:
        try:
            return self._output_store.get_for_mission(mission_id)
        except SQLAlchemyError:
            return []

    def audit(
        self,
        mission_id: str,
        event_type: str | None = None,
        status: str | None = None,
    ) -> list[MissionAuditEntry]:
        try:
            return self._audit_store.list_for_mission(
                mission_id,
                event_type=event_type,
                status=status,
            )
        except SQLAlchemyError:
            return []

    def _audit(
        self,
        mission_id: str,
        event_type: str,
        message: str,
        status: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        from uuid import uuid4

        self._audit_store.append(
            MissionAuditEntry(
                id=str(uuid4()),
                mission_id=mission_id,
                event_type=event_type,
                message=message,
                status=status,
                metadata=metadata or {},
            )
        )

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

    async def _build_autonomous_request(
        self,
        mission: CompanyMission,
        plan: MissionPlan,
    ) -> AutonomousProjectRequest:
        generated = await self._generator.generate(mission.name, mission.objective)
        return AutonomousProjectRequest(
            mission=CEOMission(
                mission_id=mission.id,
                objective=mission.objective,
                constraints=tuple(mission.constraints),
            ),
            research_query=mission.objective,
            project_request=ProjectCreateRequest(
                name=mission.name,
                description=mission.objective,
                objective=mission.objective,
            ),
            manager_mission=ManagerMission(
                name=mission.name,
                objective=mission.objective,
            ),
            tasks=(
                TaskPlanItem(
                    title=f"Implement {mission.name}",
                    description=mission.objective,
                    priority="high",
                ),
            ),
            qa_request=QATestRequest(
                command=generated.test_command,
                working_directory=".",
            ),
            files=generated.files,
        )

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
                        or (
                            result.output
                            if result and result.success
                            else result.error if result else "Execution stopped"
                        )
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
