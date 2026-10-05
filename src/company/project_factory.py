from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from src.company.events.events import CompanyEvent
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.models import MissionPlan
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus, transition_job
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator


class FactoryStore(Protocol):
    def save(self, project: FactoryProject) -> None: ...
    def load_pending(self) -> list[dict]: ...


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
    queue: list[FactoryProject] = field(default_factory=list)
    _running: bool = field(default=False, init=False, repr=False)

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
        if any(item.mission.id == mission.id for item in self.queue):
            raise ValueError(f"Mission '{mission.id}' is already queued")
        if job is not None and job.status in {
            MissionJobStatus.QUEUED,
            MissionJobStatus.COMPLETED,
            MissionJobStatus.CANCELLED,
        }:
            raise ValueError(
                f"Mission '{mission.id}' already has lifecycle state '{job.status.value}'"
            )
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
        self.queue.append(project)
        self._save(project)
        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="FACTORY_PROJECT_QUEUED",
                message=f"Project queued: {mission.name}",
                project_id=f"project:{mission.id}",
            )
        )
        return project

    async def run_next(self, max_stages: int | None = None, max_retries: int = 2) -> FactoryProject | None:
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

        if self.orchestrator.state.status.value != "running":
            self.controller.start(project.mission)

        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="FACTORY_PROJECT_STARTED",
                message=f"Factory started project: {project.mission.name}",
                project_id=f"project:{project.mission.id}",
            )
        )

        try:
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
                self.queue.insert(0, project)
                self.orchestrator.stop()
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
                self.queue.insert(0, project)
                self.orchestrator.stop()
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
        try:
            while self.queue and (max_projects is None or len(completed) < max_projects):
                project = await self.run_next(max_stages=max_stages, max_retries=max_retries)
                if project is None:
                    break
                completed.append(project)
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
