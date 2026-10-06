from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from src.company.audit import MissionAuditEntry
from src.company.events.events import CompanyEvent
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.models import MissionPlan
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus, transition_job
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_outputs import ProjectOutputManifest

if TYPE_CHECKING:
    from src.company.autonomous_factory_runner import FactoryAutonomousRunner


class FactoryStore(Protocol):
    def save(self, project: FactoryProject) -> None: ...
    def load_pending(self) -> list[dict]: ...


class MissionAuditStoreProtocol(Protocol):
    def append(self, entry: MissionAuditEntry) -> None: ...


class ProjectOutputStoreProtocol(Protocol):
    def save(self, manifest: ProjectOutputManifest) -> None: ...


class MissionJobStoreProtocol(Protocol):
    def get(self, job_id: str) -> MissionJob | None: ...
    def save(self, job: MissionJob) -> None: ...


@dataclass
class FactoryProject:
    mission: CompanyMission
    plan: MissionPlan
    status: str = "queued"
    stages_executed: int = 0
    attempts: int = 0
    last_error: str | None = None


@dataclass
class ProjectFactory:
    """Persistent, sequential project factory with bounded retry scheduling."""

    orchestrator: CompanyOrchestrator
    controller: MissionController
    pipeline: MissionExecutionPipeline
    store: FactoryStore | None = None
    job_store: MissionJobStoreProtocol | None = None
    audit_store: MissionAuditStoreProtocol | None = None
    output_store: ProjectOutputStoreProtocol | None = None
    autonomous_runner: FactoryAutonomousRunner | None = None
    queue: list[FactoryProject] = field(default_factory=list)
    _running: bool = field(default=False, init=False, repr=False)
    _last_autonomous_result: object | None = field(default=None, init=False, repr=False)

    def restore(self) -> int:
        if self.store is None:
            return 0
        restored = 0
        for item in self.store.load_pending():
            self.queue.append(FactoryProject(**item))
            restored += 1
        return restored

    def enqueue(self, mission: CompanyMission) -> FactoryProject:
        plan = build_mission_plan(mission)
        job = self._load_job(mission.id)
        if job is not None and job.status in {
            MissionJobStatus.QUEUED,
            MissionJobStatus.COMPLETED,
            MissionJobStatus.CANCELLED,
        }:
            raise ValueError(
                f"Mission '{mission.id}' already has lifecycle state '{job.status.value}'"
            )
        existing = next(
            (item for item in self.queue if item.mission.id == mission.id),
            None,
        )
        if existing is not None:
            # A repeated factory-run request should execute this mission next,
            # rather than failing because it is already queued.
            self.queue.remove(existing)
            self.queue.insert(0, existing)
            return existing
        if job is not None and job.status == MissionJobStatus.RUNNING and self._running:
            raise ValueError(f"Mission '{mission.id}' is already running in the factory")
        if job is None:
            self._save_job(
                MissionJob(
                    id=mission.id,
                    mission=mission,
                    plan=plan,
                    status=MissionJobStatus.QUEUED,
                    message=f"Project queued: {mission.name}",
                )
            )
        else:
            self._save_job(
                transition_job(job, MissionJobStatus.QUEUED, f"Project re-queued: {mission.name}")
            )
        project = FactoryProject(mission=mission, plan=plan)
        # A newly submitted mission is an explicit run request. Prioritize it over
        # restored/stale queued work so the factory-run API executes the requested mission.
        self.queue.insert(0, project)
        self._save(project)
        self._audit(
            mission.id,
            "MISSION_QUEUED",
            f"Project queued: {mission.name}",
            MissionJobStatus.QUEUED.value,
        )
        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="FACTORY_PROJECT_QUEUED",
                message=f"Project queued: {mission.name}",
                project_id=f"project:{mission.id}",
            )
        )
        return project

    def cancel(self, mission_id: str) -> MissionJob:
        job = self._load_job(mission_id)
        if job is None:
            raise KeyError(mission_id)
        if job.status != MissionJobStatus.QUEUED:
            raise ValueError(
                f"Mission '{mission_id}' cannot be cancelled from '{job.status.value}'"
            )
        remaining: list[FactoryProject] = []
        for item in self.queue:
            if item.mission.id == mission_id:
                item.status = "cancelled"
                self._save(item)
            else:
                remaining.append(item)
        self.queue = remaining
        cancelled = transition_job(
            job,
            MissionJobStatus.CANCELLED,
            f"Mission cancelled: {job.mission.name}",
        )
        self._save_job(cancelled)
        self._audit(mission_id, "MISSION_CANCELLED", cancelled.message, cancelled.status.value)
        return cancelled

    def retry(self, mission_id: str) -> MissionJob:
        job = self._load_job(mission_id)
        if job is None:
            raise KeyError(mission_id)
        if job.status not in {MissionJobStatus.FAILED, MissionJobStatus.BLOCKED}:
            raise ValueError(
                f"Mission '{mission_id}' cannot be retried from '{job.status.value}'"
            )
        self.queue = [item for item in self.queue if item.mission.id != mission_id]
        queued = transition_job(
            job,
            MissionJobStatus.QUEUED,
            f"Mission manually re-queued: {job.mission.name}",
        )
        self._save_job(queued)
        project = FactoryProject(
            mission=queued.mission,
            plan=queued.plan,
            attempts=queued.attempts,
        )
        self.queue.append(project)
        self._save(project)
        self._audit(mission_id, "MISSION_REQUEUED", queued.message, queued.status.value)
        return queued

    def _reset_for_retry(self, project: FactoryProject) -> None:
        """Reset transient execution state before retrying a project."""
        for step in project.plan.steps:
            if step.status in {"failed", "running"}:
                step.status = "planned"

        project.last_error = None
        self._last_autonomous_result = None
        self.orchestrator.stop()

    async def run_next(
        self,
        max_stages: int | None = None,
        max_retries: int = 2,
    ) -> FactoryProject | None:
        if not self.queue:
            return None

        project = self.queue.pop(0)
        project.status = "running"
        project.attempts += 1
        project.last_error = None
        self._save(project)
        job = self._load_job(project.mission.id)
        if job is not None:
            self._save_job(
                transition_job(
                    job.model_copy(update={"attempts": project.attempts}),
                    MissionJobStatus.RUNNING,
                    f"Factory attempt {project.attempts} started: {project.mission.name}",
                )
            )
            self._audit(
                project.mission.id,
                "MISSION_RUNNING",
                f"Factory attempt {project.attempts} started: {project.mission.name}",
                MissionJobStatus.RUNNING.value,
                {"attempt": project.attempts},
            )

        if self.orchestrator.state.status.value != "running":
            self.controller.start(project.mission)

        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="FACTORY_PROJECT_STARTED",
                message=f"Factory started project: {project.mission.name}",
                project_id=f"project:{project.mission.id}",
            )
        )

        self._last_autonomous_result = None
        try:
            if self.autonomous_runner is not None:
                autonomous_result = await self.autonomous_runner.run(
                    project.mission,
                    project.plan,
                )
                for step in project.plan.steps:
                    step.status = "completed"
                results = [
                    type(
                        "FactoryStageResult",
                        (),
                        {
                            "success": (
                                getattr(stage.status, "value", stage.status) == "completed"
                            )
                        },
                    )()
                    for stage in autonomous_result.stages
                ]
                self._last_autonomous_result = autonomous_result
            else:
                results = await self.pipeline.execute_mission(
                    project.mission,
                    project.plan,
                    max_stages=max_stages,
                )
        except Exception as exc:
            project.last_error = str(exc)
            results = []
        project.stages_executed += len(results)

        if all(result.success for result in results) and all(
            step.status == "completed" for step in project.plan.steps
        ):
            project.status = "completed"
            self.orchestrator.stop()
            self._save_output_manifest(project, "completed")
            self._transition_job(
                project,
                MissionJobStatus.COMPLETED,
                f"Project completed: {project.mission.name}",
            )
            event_type = "FACTORY_PROJECT_COMPLETED"
        elif self.orchestrator.state.status.value == "blocked":
            project.last_error = project.last_error or "Project execution blocked"
            if project.attempts <= max_retries:
                project.status = "queued"
                self._reset_for_retry(project)
                self.queue.insert(0, project)
                self._transition_job(
                    project,
                    MissionJobStatus.QUEUED,
                    f"Retry queued after blocked attempt: {project.mission.name}",
                )
                event_type = "FACTORY_PROJECT_RETRY_QUEUED"
            else:
                project.status = "blocked"
                event_type = "FACTORY_PROJECT_BLOCKED"
        elif project.last_error:
            if project.attempts <= max_retries:
                project.status = "queued"
                self._reset_for_retry(project)
                self.queue.insert(0, project)
                self._transition_job(
                    project,
                    MissionJobStatus.QUEUED,
                    f"Retry queued after failed attempt: {project.mission.name}",
                )
                event_type = "FACTORY_PROJECT_RETRY_QUEUED"
            else:
                project.status = "blocked"
                self.orchestrator.block(project.last_error)
                self._transition_job(
                    project,
                    MissionJobStatus.BLOCKED,
                    f"Project blocked after retries: {project.mission.name}",
                )
                event_type = "FACTORY_PROJECT_BLOCKED"
        else:
            project.status = "queued"
            self._transition_job(
                project,
                MissionJobStatus.QUEUED,
                f"Project paused and re-queued: {project.mission.name}",
            )
            event_type = "FACTORY_PROJECT_PAUSED"
            self.queue.insert(0, project)

        self._save(project)
        job = self._load_job(project.mission.id)
        self._audit(
            project.mission.id,
            event_type,
            f"Factory project {project.status}: {project.mission.name}",
            job.status.value if job is not None else None,
            {"attempt": project.attempts, "stages_executed": project.stages_executed},
        )
        self.orchestrator.events.publish(
            CompanyEvent(
                event_type=event_type,
                message=f"Factory project {project.status}: {project.mission.name}",
                project_id=f"project:{project.mission.id}",
            )
        )
        return project

    async def run(
        self,
        max_projects: int | None = None,
        max_stages: int | None = None,
        max_retries: int = 2,
    ) -> list[FactoryProject]:
        if self._running:
            raise RuntimeError("Factory is already running")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self._running = True
        completed: list[FactoryProject] = []
        completed_ids: set[str] = set()
        try:
            while self.queue and (
                max_projects is None or len(completed) < max_projects
            ):
                project = await self.run_next(
                    max_stages=max_stages,
                    max_retries=max_retries,
                )
                if project is None:
                    break
                if project.status != "queued" and project.mission.id not in completed_ids:
                    completed.append(project)
                    completed_ids.add(project.mission.id)
                if project.status == "blocked":
                    break
            self.orchestrator.events.publish(
                CompanyEvent(
                    event_type="FACTORY_RUN_COMPLETED",
                    message=f"Factory run completed: {len(completed)} project(s)",
                )
            )
            return completed
        finally:
            self._running = False

    def _save_output_manifest(self, project: FactoryProject, status: str) -> None:
        if self.output_store is None:
            return
        result = self._last_autonomous_result
        pipeline_result = getattr(result, "pipeline", None)
        pipeline_project = getattr(pipeline_result, "project", None)
        self.output_store.save(
            ProjectOutputManifest(
                id=str(uuid4()),
                mission_id=project.mission.id,
                project_id=getattr(pipeline_project, "id", f"project:{project.mission.id}"),
                name=project.mission.name,
                status=status,
                repository=getattr(pipeline_project, "repository", None),
                github_message=getattr(pipeline_result, "github_message", None),
                memory_id=getattr(pipeline_result, "memory_id", None),
            )
        )

    def _audit(
        self,
        mission_id: str,
        event_type: str,
        message: str,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.audit_store is not None:
            self.audit_store.append(
                MissionAuditEntry(
                    id=str(uuid4()),
                    mission_id=mission_id,
                    event_type=event_type,
                    message=message,
                    status=status,
                    metadata=metadata or {},
                )
            )

    def _save(self, project: FactoryProject) -> None:
        if self.store is not None:
            self.store.save(project)

    def _load_job(self, mission_id: str) -> MissionJob | None:
        if self.job_store is None:
            return None
        return self.job_store.get(mission_id)

    def _save_job(self, job: MissionJob) -> None:
        if self.job_store is not None:
            self.job_store.save(job)

    def _transition_job(
        self,
        project: FactoryProject,
        status: MissionJobStatus,
        message: str,
    ) -> None:
        job = self._load_job(project.mission.id)
        if job is not None:
            self._save_job(
                transition_job(
                    job.model_copy(update={"attempts": project.attempts}),
                    status,
                    message,
                )
            )
