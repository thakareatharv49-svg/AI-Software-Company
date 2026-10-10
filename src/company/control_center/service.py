from __future__ import annotations

import asyncio
import re
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
from src.config.settings import settings
from src.github.models.contracts import GitHubRepository
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
        # Refresh the UI projection from durable jobs before serving the list.
        # The factory updates MissionJob as it runs; without this sync the list
        # could remain "queued" after the job has already completed.
        try:
            jobs = self._job_store.list_all()
            for job in jobs:
                self._jobs[job.id] = job
                self._sync_mission_from_job(job)
        except SQLAlchemyError:
            pass

        with self._lock:
            return sorted(
                self._missions.values(),
                key=lambda item: item.updated_at,
                reverse=True,
            )

    def submit_mission(
        self, submission: MissionSubmission, *, workspace_id: str | None = "00000000-0000-4000-8000-000000000001"
    ) -> MissionRecord:
        with self._lock:
            if self._orchestrator.state.status.value == "running":
                raise RuntimeError("Company is already running a mission")
            mission = CompanyMission(
                name=submission.name.strip(),
                objective=submission.objective.strip(),
                constraints=[item.strip() for item in submission.constraints if item.strip()],
            )
            # Mission creation must only register the work. The factory-run
            # endpoint owns execution and ProjectFactory.run_next() will start
            # the orchestrator at the moment the queued mission actually runs.
            plan = self._mission_controller.prepare(mission)
            now = datetime.now(UTC)
            message = f"Mission queued: {mission.name}"
            record = MissionRecord(
                mission=mission,
                status=MissionJobStatus.QUEUED.value,
                message=message,
                created_at=now,
                updated_at=now,
                plan=plan,
            )
            self._missions[mission.id] = record
            job = MissionJob(
                id=mission.id,
                mission=mission,
                plan=plan,
                status=MissionJobStatus.QUEUED,
                message=message,
                workspace_id=workspace_id,
            )
            self._jobs[mission.id] = job
            try:
                self._job_store.save(job)
                self._audit(
                    mission.id,
                    "MISSION_CREATED",
                    message,
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
            # Do not cancel an asyncio task that owns asyncio.to_thread(). Cancelling
            # the task does not stop the underlying worker thread, so doing that here
            # can create two factory runs against the same database and workspace.
            # Keep the current run authoritative and let the caller retry once it is
            # idle.
            job = self.mission_job(mission_id) if mission_id is not None else None
            if mission_id is not None and job is None:
                raise KeyError(mission_id)
            if job is not None and job.status == MissionJobStatus.RUNNING:
                raise RuntimeError(
                    f"Mission '{mission_id}' is already running in the factory"
                )
            raise RuntimeError("Factory is already running; try again when it is idle")

        # The dashboard's launch/retry action names one specific mission. Put that
        # mission first without changing FIFO order for ordinary batch factory runs.
        if mission_id is not None:
            self._factory.prioritize_mission(mission_id)

        async def runner() -> None:
            try:
                # Keep the factory on the application's event loop. The control
                # center, factory, orchestrator, event bus, and autonomous runner
                # are one shared object graph; moving execution into asyncio.run()
                # on a worker thread creates a second event loop and can detach
                # loop-bound async state from the HTTP application.
                await self._factory.run(
                    max_projects=max_projects,
                    max_stages=max_stages,
                    max_retries=max_retries,
                )
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

        # Start the factory in the background without creating a second event
        # loop. The HTTP request returns immediately while the factory continues
        # on the application's loop and shares the same async context.
        self._factory_task = asyncio.create_task(runner())

    def factory_running(self) -> bool:
        return self._factory_task is not None and not self._factory_task.done()

    def enqueue_factory_mission(self, mission_id: str) -> None:
        record = self._get_mission(mission_id)
        if not self._factory.has_queued_mission(mission_id):
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

    def delete_queued_and_blocked_missions(self) -> dict[str, object]:
        """Delete queued/blocked mission records without touching products or output files."""
        if self.factory_running():
            raise RuntimeError("Stop the factory before deleting queued or blocked missions")

        jobs = self._job_store.list_all()
        mission_ids = {
            job.id for job in jobs
            if job.status in {MissionJobStatus.QUEUED, MissionJobStatus.BLOCKED}
        }
        if not mission_ids:
            return {"deleted_count": 0, "deleted_ids": []}

        self._factory.remove_missions(mission_ids)
        self._job_store.delete_many(mission_ids)
        with self._lock:
            for mission_id in mission_ids:
                self._jobs.pop(mission_id, None)
                self._missions.pop(mission_id, None)

        return {"deleted_count": len(mission_ids), "deleted_ids": sorted(mission_ids)}

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

        github_repository = None
        pull_request_head = None
        repository_name = None
        if (
            settings.github_allow_writes
            and settings.github_token
            and settings.github_repository_owner
        ):
            slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", mission.name.strip())
            slug = re.sub(r"-{2,}", "-", slug).strip("-._") or "generated-project"
            # Keep names stable and unique enough for repeated missions with
            # the same human-readable project name.
            repository_name_only = f"{slug}-{mission.id[:8]}"
            github_repository = GitHubRepository(
                owner=settings.github_repository_owner,
                name=repository_name_only,
                default_branch=settings.github_default_branch,
            )
            # Compatibility field: the factory now publishes directly to the default branch.
            pull_request_head = settings.github_default_branch
            repository_name = (
                f"{settings.github_repository_owner}/{repository_name_only}"
            )

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
                repository=repository_name,
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
            github_repository=github_repository,
            pull_request_head=pull_request_head,
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
