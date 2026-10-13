from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import signature
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from src.company.audit import MissionAuditEntry
from src.company.events.events import CompanyEvent
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.models import MissionPlan
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import (
    MissionJob,
    MissionJobStatus,
    recover_running_job,
    recover_running_plan,
    transition_job,
)
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_outputs import ProjectOutputManifest
from src.security.redaction import redact_sensitive_text, redact_sensitive_value

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
    retry_feedback: str | None = None


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
    execution_timeout_seconds: float = 1800.0
    queue: list[FactoryProject] = field(default_factory=list)
    _running: bool = field(default=False, init=False, repr=False)
    _active_project: FactoryProject | None = field(default=None, init=False, repr=False)
    _last_autonomous_result: object | None = field(default=None, init=False, repr=False)

    def restore(self) -> int:
        if self.store is None:
            return 0
        restored = 0
        known_ids = {item.mission.id for item in self.queue}
        for item in self.store.load_pending():
            # Treat each snapshot as an independent recovery unit. A malformed
            # entry from a custom/legacy store must not prevent later valid
            # missions from being restored after restart.
            try:
                mission_id = item["mission"].id
                if mission_id in known_ids:
                    continue
                project = FactoryProject(**item)
            except (AttributeError, KeyError, TypeError, ValueError):
                import logging

                logging.getLogger(__name__).error(
                    "Skipping malformed pending factory snapshot"
                )
                continue
            # Older snapshots may predate write-time redaction. Sanitize text
            # before any restored mission or plan can be reused by an agent.
            project.mission = self._safe_mission(project.mission)
            project.plan = self._safe_plan(project.plan)
            project.last_error = (
                self._safe_error_detail(project.last_error)
                if project.last_error
                else None
            )
            project.retry_feedback = (
                self._safe_error_detail(project.retry_feedback)
                if project.retry_feedback
                else None
            )
            job = self._load_job(project.mission.id)
            if job is not None:
                safe_job_mission = self._safe_mission(job.mission)
                safe_job_plan = self._safe_plan(job.plan)
                if (
                    safe_job_mission.model_dump() != job.mission.model_dump()
                    or safe_job_plan.model_dump() != job.plan.model_dump()
                ):
                    job = job.model_copy(
                        update={"mission": safe_job_mission, "plan": safe_job_plan}
                    )
                    self._save_job(job)
            # The project store can contain a stale snapshot if shutdown or
            # cancellation happened between persistence operations. Durable
            # terminal job state wins: never resurrect completed, failed,
            # blocked, or cancelled work into the active queue.
            if job is not None and job.status in {
                MissionJobStatus.COMPLETED,
                MissionJobStatus.FAILED,
                MissionJobStatus.BLOCKED,
                MissionJobStatus.CANCELLED,
            }:
                delete_many = getattr(self.store, "delete_many", None)
                if callable(delete_many):
                    delete_many({project.mission.id})
                continue
            # A queued durable job can also be newer than its project snapshot
            # (for example, after a bounded pause or a crash during persistence).
            # Prefer its latest plan and attempt count without resetting progress.
            if job is not None and job.status == MissionJobStatus.QUEUED:
                durable_plan = job.plan.model_copy(deep=True)
                project_changed = (
                    project.plan.model_dump() != durable_plan.model_dump()
                    or project.attempts < job.attempts
                )
                project.plan = durable_plan
                project.attempts = max(project.attempts, job.attempts)
                if project_changed:
                    self._save(project)

            # The project snapshot and durable job are written separately, so
            # a crash can leave either one behind. If the durable job says RUNNING,
            # prefer its latest plan when the project snapshot still says queued;
            # progress updates persist to both stores, but the job can be newer.
            if job is not None and job.status == MissionJobStatus.RUNNING:
                if project.status != "running":
                    project.plan = job.plan.model_copy(deep=True)
                    project.attempts = max(project.attempts, job.attempts)
                project.plan = recover_running_plan(project.plan)
                recovered_job = recover_running_job(
                    job.model_copy(update={"plan": project.plan})
                )
                self._save_job(recovered_job)

            # Never restore an interrupted project as actively running. Reclaim
            # it as queued and reset only in-flight stages, preserving completed
            # work from the freshest available plan snapshot.
            if project.status == "running" or (
                job is not None and job.status == MissionJobStatus.RUNNING
            ):
                project.plan = recover_running_plan(project.plan)
                project.status = "queued"
                interrupted_detail = next(
                    (
                        step.detail.strip()
                        for step in project.plan.steps
                        if step.detail and step.detail.strip()
                        and step.status == "failed"
                    ),
                    None,
                )
                # Retry feedback is fed back into the model on the next
                # attempt. Older persisted snapshots may predate write-time
                # redaction, so sanitize recovered diagnostics before reuse.
                project.retry_feedback = (
                    self._safe_error_detail(interrupted_detail)[:2000]
                    if interrupted_detail
                    else None
                )
                self._save(project)
            self._save(project)
            self.queue.append(project)
            known_ids.add(project.mission.id)
            restored += 1
        return restored

    @staticmethod
    def _safe_mission(mission: CompanyMission) -> CompanyMission:
        """Redact and bound mission text before persistence or planning."""
        def safe_text(value: str, limit: int) -> str:
            return redact_sensitive_text(str(value))[:limit]

        return mission.model_copy(
            update={
                "name": safe_text(mission.name, 500),
                "objective": safe_text(mission.objective, 8000),
                "constraints": [
                    safe_text(constraint, 2000)
                    for constraint in mission.constraints
                ],
            }
        )

    @staticmethod
    def _safe_plan(plan: MissionPlan) -> MissionPlan:
        """Redact legacy free-text plan fields without resetting execution progress."""
        safe = plan.model_copy(deep=True)

        def safe_text(value: str, limit: int) -> str:
            return redact_sensitive_text(str(value))[:limit]

        # Legacy snapshots may contain unbounded user/model text. Bound every
        # free-text field before the plan is restored into memory or reused.
        for field_name, limit in (
            ("name", 500),
            ("objective", 8000),
            ("qa_status", 120),
            ("qa_evidence", 5200),
            ("security_status", 120),
            ("security_summary", 1000),
            ("security_evidence", 2000),
        ):
            value = getattr(safe, field_name, None)
            if isinstance(value, str):
                setattr(safe, field_name, safe_text(value, limit))
        safe.constraints = [safe_text(value, 2000) for value in safe.constraints]
        safe.acceptance_criteria = [
            safe_text(value, 4000) for value in safe.acceptance_criteria
        ]
        safe.qa_command = [safe_text(value, 500) for value in safe.qa_command]
        for step in safe.steps:
            step.objective = safe_text(step.objective, 2000)
            step.agent_role = safe_text(step.agent_role, 120)
            step.status = safe_text(step.status, 120)
            if step.detail:
                step.detail = safe_text(step.detail, 4000)
        for task in safe.engineering_tasks:
            task.title = safe_text(task.title, 500)
            task.requirement = safe_text(task.requirement, 4000)
            task.workstream = safe_text(task.workstream, 200)
            task.agent_role = safe_text(task.agent_role, 120)
            task.acceptance_check = safe_text(task.acceptance_check, 2000)
            task.status = safe_text(task.status, 120)
        return safe

    def enqueue(self, mission: CompanyMission) -> FactoryProject:
        job = self._load_job(mission.id)
        if job is None:
            # Treat the initial submission as a trust boundary: mission text is
            # copied into durable jobs, plans, audit events, and model prompts.
            mission = self._safe_mission(mission)
        # If the durable job is already queued but its in-memory/project snapshot
        # is missing, treat that job as the source of truth. Rebuilding a fresh
        # plan here would silently erase recovered stage progress and attempts.
        if job is not None and job.status == MissionJobStatus.QUEUED:
            mission = job.mission
            plan = job.plan.model_copy(deep=True)
        else:
            plan = build_mission_plan(mission)
        existing = next(
            (item for item in self.queue if item.mission.id == mission.id),
            None,
        )
        if existing is not None:
            raise ValueError(
                f"Mission '{mission.id}' already has lifecycle state 'queued'"
            )
        if job is not None and job.status in {
            MissionJobStatus.COMPLETED,
            MissionJobStatus.CANCELLED,
            MissionJobStatus.FAILED,
            MissionJobStatus.BLOCKED,
        }:
            raise ValueError(
                f"Mission '{mission.id}' already has lifecycle state '{job.status.value}'"
            )
        if job is not None and job.status == MissionJobStatus.RUNNING:
            # A durable RUNNING record may belong to a worker interrupted by a
            # process restart. Enqueue must not overwrite it with a fresh plan;
            # restore() is responsible for recovering its in-flight progress.
            raise ValueError(
                f"Mission '{mission.id}' is already running; recover it before re-enqueueing"
            )
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
            if job.status == MissionJobStatus.QUEUED:
                self._save_job(job)
            else:
                self._save_job(
                    transition_job(
                        job,
                        MissionJobStatus.QUEUED,
                        f"Project re-queued: {mission.name}",
                    )
                )
        project = FactoryProject(
            mission=mission,
            plan=plan,
            attempts=job.attempts if job is not None and job.status == MissionJobStatus.QUEUED else 0,
        )
        # Preserve FIFO ordering: the first submitted mission must execute first.
        # A terminal failure is recorded per mission; it must not discard unrelated work.
        self.queue.append(project)
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

    def has_queued_mission(self, mission_id: str) -> bool:
        return any(item.mission.id == mission_id for item in self.queue)

    def remove_missions(self, mission_ids: set[str]) -> None:
        """Remove explicitly selected non-running missions from the queue and store."""
        if not mission_ids:
            return
        active = self._active_project
        if active is not None and active.mission.id in mission_ids:
            raise ValueError("Cannot delete a mission that is currently running")
        if any(
            item.mission.id in mission_ids and item.status == "running"
            for item in self.queue
        ):
            raise ValueError("Cannot delete a mission that is currently running")
        removed = [
            item for item in self.queue if item.mission.id in mission_ids
        ]
        self.queue = [
            item for item in self.queue if item.mission.id not in mission_ids
        ]
        for project in removed:
            job = self._load_job(project.mission.id)
            if job is not None and job.status == MissionJobStatus.QUEUED:
                cancelled = transition_job(
                    job,
                    MissionJobStatus.CANCELLED,
                    f"Mission removed from queue: {project.mission.name}",
                )
                self._save_job(cancelled)
                self._audit(
                    project.mission.id,
                    "MISSION_REMOVED_FROM_QUEUE",
                    cancelled.message,
                    cancelled.status.value,
                )
        delete_many = getattr(self.store, "delete_many", None)
        if callable(delete_many):
            delete_many(mission_ids)

    def prioritize_mission(self, mission_id: str) -> None:
        """Run an explicitly requested mission before older restored queue entries."""
        index = next(
            (i for i, item in enumerate(self.queue) if item.mission.id == mission_id),
            None,
        )
        if index is None:
            raise KeyError(f"Queued mission '{mission_id}' not found")
        if index:
            self.queue.insert(0, self.queue.pop(index))

    def retry(self, mission_id: str) -> MissionJob:
        job = self._load_job(mission_id)
        if job is None:
            raise KeyError(mission_id)
        if job.status not in {MissionJobStatus.FAILED, MissionJobStatus.BLOCKED}:
            raise ValueError(
                f"Mission '{mission_id}' cannot be retried from '{job.status.value}'"
            )
        self.queue = [item for item in self.queue if item.mission.id != mission_id]
        # Capture the concrete failed-stage diagnosis before resetting the plan.
        # Otherwise a manual retry silently loses the feedback used by automatic
        # retries and can repeat the same failed generation attempt.
        retry_feedback = next(
            (
                step.detail.strip()
                for step in job.plan.steps
                if step.status == "failed" and step.detail and step.detail.strip()
            ),
            None,
        )
        queued = transition_job(
            job,
            MissionJobStatus.QUEUED,
            f"Mission manually re-queued: {job.mission.name}",
        )
        self._save_job(queued)
        # A manual retry starts a fresh attempt. Persist the reset plan as well
        # as the queued job so stale failed/running steps cannot poison the retry.
        plan = queued.plan.model_copy(deep=True)
        for step in plan.steps:
            # Manual retry restarts the mission from its first lifecycle stage.
            # Clear completed statuses too, otherwise the dashboard can display
            # stale success while the new attempt is still executing.
            if step.status != "planned" or step.detail is not None:
                step.status = "planned"
                step.detail = None
        queued = queued.model_copy(update={"plan": plan})
        self._save_job(queued)
        project = FactoryProject(
            mission=queued.mission,
            plan=plan,
            attempts=queued.attempts,
            retry_feedback=(self._safe_error_detail(retry_feedback)[:2000] if retry_feedback else None),
        )
        self.queue.append(project)
        self._save(project)
        self._audit(mission_id, "MISSION_REQUEUED", queued.message, queued.status.value)
        return queued

    def revise(self, mission_id: str, feedback: str) -> MissionJob:
        """Queue a new build revision while preserving the mission identity and history."""
        if self._running:
            raise RuntimeError("Wait for the active factory run to finish before revising a product")
        job = self._load_job(mission_id)
        if job is None:
            raise KeyError(mission_id)
        if job.status != MissionJobStatus.COMPLETED:
            raise ValueError(f"Mission '{mission_id}' cannot be revised from '{job.status.value}'")
        feedback = redact_sensitive_text(feedback.strip())
        if not feedback:
            raise ValueError("Revision feedback cannot be blank")
        if len(feedback) > 10000:
            raise ValueError("Revision feedback exceeds 10000 characters")

        # Older missions may have been stored before write-time redaction.
        # Sanitize the full objective, not only new feedback, before persisting
        # it or sending it back through the planner/model pipeline.
        revised_objective = redact_sensitive_text(
            f"{job.mission.objective.rstrip()}\n\n"
            "OWNER-REQUESTED REVISION FEEDBACK:\n"
            f"{feedback}"
        )
        safe_original = self._safe_mission(job.mission)
        revised_mission = safe_original.model_copy(
            update={"objective": revised_objective}
        )
        plan = build_mission_plan(revised_mission)
        now = datetime.now(UTC)
        queued_job = job.model_copy(update={
            "mission": revised_mission,
            "plan": plan,
            "status": MissionJobStatus.QUEUED,
            "message": f"Revision queued: {revised_mission.name}",
            "attempts": 0,
            "updated_at": now,
        })
        self.queue = [item for item in self.queue if item.mission.id != mission_id]
        project = FactoryProject(mission=revised_mission, plan=plan)
        self._save_job(queued_job)
        self._save(project)
        self.queue.append(project)
        self._last_autonomous_result = None
        self.orchestrator.stop()
        self._audit(
            mission_id,
            "MISSION_REVISION_REQUESTED",
            f"Owner requested a new product revision: {revised_mission.name}",
            MissionJobStatus.QUEUED.value,
            {"feedback": feedback},
        )
        self.orchestrator.events.publish(
            CompanyEvent(
                event_type="MISSION_REVISION_REQUESTED",
                message=f"Revision queued: {revised_mission.name}",
                project_id=f"project:{mission_id}",
            )
        )
        return queued_job

    def _reset_for_retry(
        self,
        project: FactoryProject,
        *,
        reset_completed: bool = False,
    ) -> None:
        """Reset transient progress, optionally restarting the full lifecycle."""
        for step in project.plan.steps:
            # A bounded max_stages run is a deliberate pause/resume, not a retry
            # from scratch. Preserve its completed stages; real failed attempts
            # must clear all progress so the dashboard reflects the new attempt.
            should_reset = (
                step.status != "planned" or step.detail is not None
            ) and (
                reset_completed or step.status in {"failed", "running"}
            )
            if should_reset:
                step.status = "planned"
                step.detail = None

        if project.last_error:
            # Give the next generation attempt the concrete reason the previous
            # attempt failed, instead of repeating the same prompt unchanged.
            project.retry_feedback = self._safe_error_detail(project.last_error)[:2000]
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
        # Retain ownership until run_next returns so run() can finalize the mission
        # if an unexpected persistence, audit, or event error escapes the stage guard.
        self._active_project = project
        # A prior mission's pipeline must never satisfy this mission's completion check.
        self._last_autonomous_result = None
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

        self._last_autonomous_result = None
        try:
            # Keep startup inside the guarded execution path. A controller/startup
            # failure must be recorded as the real error, not misreported later as
            # a project whose stages simply remained "planned".
            if self.orchestrator.state.status.value != "running":
                self.controller.start(project.mission)

            startup_status = self.orchestrator.state.status.value
            if startup_status != "running":
                raise RuntimeError(
                    "Mission execution did not start: "
                    f"orchestrator_status={startup_status}; "
                    f"mission_id={project.mission.id}"
                )

            self.orchestrator.events.publish(
                CompanyEvent(
                    event_type="FACTORY_PROJECT_STARTED",
                    message=f"Factory started project: {project.mission.name}",
                    project_id=f"project:{project.mission.id}",
                )
            )

            attempt_mission = project.mission
            if project.retry_feedback:
                attempt_mission = project.mission.model_copy(
                    update={
                        "objective": (
                            f"{project.mission.objective.rstrip()}\n\n"
                            "AUTOMATIC RECOVERY FEEDBACK FROM THE PREVIOUS ATTEMPT:\n"
                            f"{project.retry_feedback}\n\n"
                            "Correct the reported failure while preserving all original "
                            "mission requirements. Do not omit requested features."
                        )
                    }
                )

            if self.autonomous_runner is not None:
                runner = self.autonomous_runner.run
                try:
                    supports_progress = "on_progress" in signature(runner).parameters
                except (TypeError, ValueError):
                    supports_progress = False
                if supports_progress:
                    execution = runner(
                        attempt_mission,
                        project.plan,
                        on_progress=lambda _plan: self._persist_plan_progress(project),
                    )
                else:
                    # Older adapters cannot publish stage-level progress. Mark
                    # execution as active before awaiting them so the dashboard
                    # does not display a long-running mission as entirely planned.
                    execution_step = next(
                        (
                            step
                            for step in project.plan.steps
                            if step.stage.value == "execution"
                            and step.status == "planned"
                        ),
                        None,
                    )
                    if execution_step is not None:
                        execution_step.status = "running"
                        execution_step.detail = (
                            "Autonomous runner is executing; detailed stage "
                            "telemetry is unavailable for this runner."
                        )
                        self._persist_plan_progress(project)
                    execution = runner(attempt_mission, project.plan)
                autonomous_result = await asyncio.wait_for(
                    execution,
                    timeout=self.execution_timeout_seconds,
                )
                # Capture the authoritative result immediately. Processing optional
                # stage telemetry below must never erase a completed pipeline result.
                self._last_autonomous_result = autonomous_result
                # Validate the authoritative completion signal before mutating visible
                # stage statuses; otherwise an invalid result leaves most stages falsely
                # marked completed when the mission is blocked.
                if getattr(autonomous_result, "pipeline", None) is None:
                    raise RuntimeError(
                        "Autonomous runner returned no pipeline result"
                    )
                for step in project.plan.steps:
                    step.status = "completed"
                # Stage telemetry is best-effort only. A malformed status
                # must not turn a successfully returned pipeline into a failure.
                try:
                    results = [
                        type(
                            "FactoryStageResult",
                            (),
                            {
                                "success": (
                                    str(getattr(stage.status, "value", stage.status))
                                    .strip()
                                    .casefold()
                                    == "completed"
                                )
                            },
                        )()
                        for stage in autonomous_result.stages
                    ]
                except Exception:
                    results = []
                if not results:
                    results = [
                        type(
                            "FactoryStageResult",
                            (),
                            {"success": True},
                        )()
                    ]
                # Ignore telemetry errors once the authoritative pipeline exists.
                project.last_error = None
            else:
                results = await asyncio.wait_for(
                    self.pipeline.execute_mission(
                        attempt_mission,
                        project.plan,
                        max_stages=max_stages,
                    ),
                    timeout=self.execution_timeout_seconds,
                )
        except asyncio.CancelledError:
            # Cancellation (for example, an application shutdown) bypasses
            # the ordinary Exception handler on modern Python. Re-queue the
            # active mission before propagating cancellation so persisted state
            # is not stranded as running and completed stages remain resumable.
            project.status = "queued"
            project.last_error = "Factory execution cancelled; mission re-queued for safe resume."
            project.plan = recover_running_plan(project.plan)
            if not any(item.mission.id == project.mission.id for item in self.queue):
                self.queue.insert(0, project)
            try:
                self.orchestrator.stop()
            except Exception:
                pass
            try:
                self._save(project)
            except Exception:
                pass
            try:
                job = self._load_job(project.mission.id)
                if job is not None and job.status == MissionJobStatus.RUNNING:
                    self._save_job(
                        transition_job(
                            job.model_copy(
                                update={
                                    "plan": project.plan,
                                    "attempts": project.attempts,
                                }
                            ),
                            MissionJobStatus.QUEUED,
                            f"Execution interrupted; mission safely re-queued: {project.mission.name}",
                        )
                    )
            except Exception:
                pass
            try:
                self._audit(
                    project.mission.id,
                    "MISSION_EXECUTION_CANCELLED",
                    project.last_error,
                    MissionJobStatus.QUEUED.value,
                    {"attempt": project.attempts, "recovered_for_resume": True},
                )
            except Exception:
                pass
            finally:
                self._active_project = None
            raise
        except Exception as exc:
            if isinstance(exc, TimeoutError):
                project.last_error = (
                    "TimeoutError: Factory execution exceeded "
                    f"{self.execution_timeout_seconds:g} seconds"
                )
            else:
                project.last_error = self._safe_error_detail(f"{type(exc).__name__}: {exc}")
            # Failures can occur before the autonomous runner emits its first
            # progress callback (for example, while preparing the request). Mark
            # a concrete stage and persist it so the customer dashboard does not
            # misleadingly leave every stage as "planned".
            failed_step = next(
                (step for step in project.plan.steps if step.status == "failed"),
                None,
            )
            if failed_step is None:
                active_step = next(
                    (
                        step
                        for step in project.plan.steps
                        if step.status == "running"
                    ),
                    None,
                )
                if active_step is None and self.autonomous_runner is not None:
                    # Startup can fail before the autonomous adapter emits stage
                    # telemetry. Attribute that failure to execution rather than
                    # falsely reporting that research itself failed.
                    active_step = next(
                        (
                            step
                            for step in project.plan.steps
                            if step.stage.value == "execution"
                        ),
                        None,
                    )
                if active_step is None:
                    active_step = next(
                        (
                            step
                            for step in project.plan.steps
                            if step.status == "planned"
                        ),
                        None,
                    )
                if active_step is not None:
                    active_step.status = "failed"
                    active_step.detail = project.last_error
            elif not failed_step.detail:
                failed_step.detail = project.last_error
            self._persist_plan_progress(project)
            results = []
        project.stages_executed += len(results)

        autonomous_pipeline_succeeded = (
            self._last_autonomous_result is not None
            and getattr(self._last_autonomous_result, "pipeline", None) is not None
        )
        # A returned autonomous pipeline result means the end-to-end runner
        # completed its delivery contract. Stage telemetry is diagnostic metadata
        # and must not override that authoritative result: adapters may report
        # stale/inconsistent stage statuses even when the pipeline succeeded.
        execution_succeeded = (
            autonomous_pipeline_succeeded
            or (
                all(result.success for result in results)
                and all(step.status == "completed" for step in project.plan.steps)
            )
        )

        if execution_succeeded:
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
            if project.attempts <= max_retries and max_retries > 0:
                project.status = "queued"
                self._reset_for_retry(project, reset_completed=True)
                # A transiently failing mission must not monopolize the worker.
                # Let already queued missions run before this mission's next attempt.
                self._requeue_for_fairness(project)
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
            # GitHub secondary rate limits are external/transient. Retrying the
            # entire factory immediately only creates more content-creation calls
            # and can extend the block. Leave the mission blocked so the user can
            # retry after GitHub's cooldown without regenerating the project.
            github_rate_limited = (
                "secondary rate limit" in project.last_error.lower()
                or "temporarily blocked from content creation" in project.last_error.lower()
                or "github api 403" in project.last_error.lower()
            )
            if github_rate_limited:
                project.status = "blocked"
                self.orchestrator.stop()
                self._transition_job(
                    project,
                    MissionJobStatus.BLOCKED,
                    (
                        f"Project blocked by GitHub rate limiting: {project.mission.name}. "
                        "Wait for the GitHub cooldown, then retry the mission."
                    ),
                )
                event_type = "FACTORY_PROJECT_BLOCKED_RATE_LIMIT"
            elif project.attempts <= max_retries:
                project.status = "queued"
                self._reset_for_retry(project, reset_completed=True)
                # A transiently failing mission must not monopolize the worker.
                # Let already queued missions run before this mission's next attempt.
                self._requeue_for_fairness(project)
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
                    (
                        f"Project blocked after retries: {project.mission.name}. "
                        f"Last error: {project.last_error}"
                    ),
                )
                event_type = "FACTORY_PROJECT_BLOCKED"
        else:
            # An execution that returns unsuccessful stage results or leaves plan
            # steps incomplete is a failure, not a harmless pause. Retry only when
            # budget remains; otherwise persist a terminal blocked state.
            execution_failed = (
                not results
                or any(not result.success for result in results)
                or any(step.status != "completed" for step in project.plan.steps)
            )
            if execution_failed and project.attempts > max_retries:
                project.status = "blocked"
                if not project.last_error:
                    failed_stages = [
                        f"{stage.name}: {stage.detail}"
                        for stage in getattr(self._last_autonomous_result, "stages", ())
                        if str(getattr(stage.status, "value", stage.status))
                        .strip()
                        .casefold()
                        != "completed"
                    ]
                    incomplete_steps = [
                        f"{step.stage.value}: {step.status}"
                        for step in project.plan.steps
                        if step.status != "completed"
                    ]
                    diagnostic_parts = failed_stages + incomplete_steps
                    if not diagnostic_parts:
                        diagnostic_parts.append(
                            "no failed stage details were recorded; "
                            f"orchestrator_status={self.orchestrator.state.status.value}"
                        )
                    project.last_error = (
                        "Project execution did not complete all stages: "
                        + "; ".join(diagnostic_parts)
                    )
                self.orchestrator.block(project.last_error)
                self._transition_job(
                    project,
                    MissionJobStatus.BLOCKED,
                    f"Project blocked after retries: {project.mission.name}. "
                    f"Last error: {project.last_error}",
                )
                event_type = "FACTORY_PROJECT_BLOCKED"
            elif execution_failed:
                project.status = "queued"
                self._reset_for_retry(project, reset_completed=max_stages is None)
                # Preserve FIFO fairness when resuming a paused or failed attempt.
                self._requeue_for_fairness(project)
                self._transition_job(
                    project,
                    MissionJobStatus.QUEUED,
                    f"Retry queued after failed attempt: {project.mission.name}",
                )
                event_type = "FACTORY_PROJECT_RETRY_QUEUED"
            else:
                project.status = "queued"
                self._transition_job(
                    project,
                    MissionJobStatus.QUEUED,
                    f"Project paused and re-queued: {project.mission.name}",
                )
                event_type = "FACTORY_PROJECT_PAUSED"
                # A bounded pause yields to other missions already in the queue.
                self._requeue_for_fairness(project)

        self._save(project)
        job = self._load_job(project.mission.id)
        audit_metadata = {
            "attempt": project.attempts,
            "stages_executed": project.stages_executed,
            "orchestrator_status": self.orchestrator.state.status.value,
            "execution_mode": (
                "autonomous" if self.autonomous_runner is not None else "agent_pipeline"
            ),
        }
        if project.last_error:
            audit_metadata["error"] = project.last_error
        self._audit(
            project.mission.id,
            event_type,
            f"Factory project {project.status}: {project.mission.name}",
            job.status.value if job is not None else None,
            audit_metadata,
        )
        self.orchestrator.events.publish(
            CompanyEvent(
                event_type=event_type,
                message=f"Factory project {project.status}: {project.mission.name}",
                project_id=f"project:{project.mission.id}",
            )
        )
        self._active_project = None
        return project

    def _requeue_for_fairness(self, project: FactoryProject) -> None:
        """Append a retry behind already-waiting missions without duplicating it."""
        if not any(item.mission.id == project.mission.id for item in self.queue):
            self.queue.append(project)

    @staticmethod
    def _safe_error_detail(value: str) -> str:
        """Redact and bound exception text before persisting it to mission state."""
        return redact_sensitive_text(str(value))[:4000]

    def _contain_unexpected_worker_error(
        self, project: FactoryProject, exc: Exception
    ) -> None:
        """Best-effort terminalize a mission if an error escapes run_next cleanup."""
        if project.status not in {"completed", "blocked", "cancelled"}:
            project.status = "blocked"
            project.last_error = self._safe_error_detail(
                f"Factory worker error: {type(exc).__name__}: {exc}"
            )
            active_step = next(
                (step for step in project.plan.steps if step.status == "running"),
                None,
            )
            if active_step is None:
                active_step = next(
                    (step for step in project.plan.steps if step.status == "planned"),
                    None,
                )
            if active_step is not None:
                active_step.status = "failed"
                active_step.detail = project.last_error
            try:
                self.orchestrator.stop()
            except Exception:
                pass
            try:
                self._save(project)
            except Exception:
                pass
            try:
                self._transition_job(
                    project,
                    MissionJobStatus.BLOCKED,
                    f"Project blocked after factory worker error: {project.mission.name}. "
                    f"Last error: {project.last_error}",
                )
            except Exception:
                pass
            try:
                self._audit(
                    project.mission.id,
                    "FACTORY_WORKER_ERROR",
                    f"Factory worker error: {project.mission.name}",
                    MissionJobStatus.BLOCKED.value,
                    {"error": project.last_error},
                )
            except Exception:
                pass
            try:
                self.orchestrator.events.publish(
                    CompanyEvent(
                        event_type="FACTORY_WORKER_ERROR",
                        message=f"Factory worker error: {project.mission.name}",
                        project_id=f"project:{project.mission.id}",
                    )
                )
            except Exception:
                pass
        self._active_project = None

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
                try:
                    project = await self.run_next(
                        max_stages=max_stages,
                        max_retries=max_retries,
                    )
                except Exception as exc:
                    project = self._active_project
                    if project is None:
                        raise
                    self._contain_unexpected_worker_error(project, exc)
                if project is None:
                    break
                if project.status != "queued" and project.mission.id not in completed_ids:
                    completed.append(project)
                    completed_ids.add(project.mission.id)
                # A blocked mission is terminal for that mission only. Continue
                # with other queued missions so one bad project cannot stall the factory.
                # The next run_next() call restarts the orchestrator for its next mission.
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
                product_url=(
                    f"/product/{project.mission.id}"
                    if status == "completed"
                    and getattr(pipeline_result, "browser_preview", False)
                    else None
                ),
                github_message=getattr(pipeline_result, "github_message", None),
                github_pending=getattr(pipeline_result, "github_pending", False),
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
            # Audit entries can outlive the mission snapshot and are often
            # surfaced in dashboards or incident reports. Treat messages and
            # nested metadata as untrusted text at this final persistence boundary.
            self.audit_store.append(
                MissionAuditEntry(
                    id=str(uuid4()),
                    mission_id=mission_id,
                    event_type=event_type,
                    message=redact_sensitive_text(str(message)),
                    status=status,
                    metadata=redact_sensitive_value(metadata or {}),
                )
            )

    def _save(self, project: FactoryProject) -> None:
        # Enforce the same trust boundary on every write, not just when older
        # snapshots are restored. Plans can accumulate model-generated evidence
        # and stage diagnostics during execution.
        project.mission = self._safe_mission(project.mission)
        project.plan = self._safe_plan(project.plan)
        project.last_error = (
            self._safe_error_detail(project.last_error)
            if project.last_error
            else None
        )
        project.retry_feedback = (
            self._safe_error_detail(project.retry_feedback)
            if project.retry_feedback
            else None
        )
        if self.store is not None:
            self.store.save(project)

    def _load_job(self, mission_id: str) -> MissionJob | None:
        if self.job_store is None:
            return None
        job = self.job_store.get(mission_id)
        if job is None:
            return None

        # Legacy durable records can bypass current write-time safeguards.
        # Normalize them immediately on read so retry, enqueue, dashboard, and
        # audit paths never consume unsafe nested text from a job store.
        safe_job = job.model_copy(
            update={
                "mission": self._safe_mission(job.mission),
                "plan": self._safe_plan(job.plan),
                "message": redact_sensitive_text(str(job.message))[:4000],
            }
        )
        if safe_job.model_dump() != job.model_dump():
            self._save_job(safe_job)
        return safe_job

    def _persist_plan_progress(self, project: FactoryProject) -> None:
        """Persist live stage status so the dashboard never shows stale all-planned work."""
        self._save(project)
        job = self._load_job(project.mission.id)
        if job is not None:
            self._save_job(
                job.model_copy(
                    update={
                        "plan": project.plan,
                        "updated_at": datetime.now(UTC),
                    }
                )
            )

    def _save_job(self, job: MissionJob) -> None:
        if self.job_store is not None:
            # model_copy(update=...) bypasses Pydantic validators, so sanitize
            # the nested mission/plan and diagnostic message explicitly here.
            safe_job = job.model_copy(
                update={
                    "mission": self._safe_mission(job.mission),
                    "plan": self._safe_plan(job.plan),
                    "message": redact_sensitive_text(str(job.message))[:4000],
                }
            )
            self.job_store.save(safe_job)

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
                    job.model_copy(
                        update={
                            "attempts": project.attempts,
                            "plan": project.plan,
                        }
                    ),
                    status,
                    message,
                )
            )
