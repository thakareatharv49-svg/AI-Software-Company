from __future__ import annotations

import asyncio
import math
import time
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
    MAX_MISSION_ATTEMPTS,
    MissionJob,
    MissionJobStatus,
    recover_running_job,
    recover_running_plan,
    resume_failed_plan,
    transition_job,
)
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_outputs import ProjectOutputManifest
from src.company.retry_policy import FailureClass, classify_failure
from src.company.recovery_diagnostics import build_recovery_diagnostics
from src.security.redaction import redact_sensitive_text, redact_sensitive_value

if TYPE_CHECKING:
    from src.company.autonomous_factory_runner import FactoryAutonomousRunner


def _bounded_job_attempts(value: object) -> int:
    """Bound attempts even when a legacy object bypassed Pydantic validation."""
    try:
        return min(MAX_MISSION_ATTEMPTS, max(0, int(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _durable_identity_text(value: object) -> str | None:
    """Accept only explicit non-empty string IDs from durable storage."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


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
    worker_started_at: datetime | None = None
    last_progress_at: datetime | None = None
    progress_updates: int = 0
    retry_not_before_epoch: float = 0.0


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
        if self.store is None and self.job_store is None:
            return 0
        # Materialize project snapshots inside a recovery boundary. Durable
        # mission jobs are reconciled separately below, so a project-store
        # outage does not hide recoverable jobs from the queue.
        pending: list[dict] = []
        if self.store is not None:
            try:
                pending = list(self.store.load_pending())
            except Exception:
                import logging

                logging.getLogger(__name__).error(
                    "Unable to load pending factory snapshots; trying durable job recovery"
                )
        restored = 0
        known_ids = {item.mission.id for item in self.queue}
        # Use one stable enumeration for both identity preflight and orphan
        # recovery. Calling list_all twice creates a time-of-check/time-of-use
        # gap: a changing store could pass validation, then return a different
        # identity index for enqueueing.
        durable_jobs_snapshot: list[MissionJob] | None = None

        # Validate the durable identity index before recovering *any* snapshot.
        # Per-snapshot reconciliation alone is insufficient: a direct lookup can
        # return a plausible row while enumeration reveals a duplicate/corrupt
        # mapping elsewhere in the index.
        if self.job_store is not None:
            list_all_jobs = getattr(self.job_store, "list_all", None)
            if callable(list_all_jobs):
                try:
                    indexed_jobs = list(list_all_jobs())
                    durable_jobs_snapshot = indexed_jobs
                    seen_durable_ids: set[str] = set()
                    seen_embedded_ids: set[str] = set()
                    for candidate in indexed_jobs:
                        durable_id = _durable_identity_text(candidate.id)
                        embedded_id = _durable_identity_text(candidate.mission.id)
                        if (
                            not durable_id
                            or not embedded_id
                            or durable_id != embedded_id
                            or durable_id in seen_durable_ids
                            or embedded_id in seen_embedded_ids
                        ):
                            raise ValueError("ambiguous durable mission identity index")
                        seen_durable_ids.add(durable_id)
                        seen_embedded_ids.add(embedded_id)
                except Exception:
                    import logging

                    logging.getLogger(__name__).error(
                        "Durable mission identity preflight failed; skipping factory snapshot recovery"
                    )
                    return 0

        for item in pending:
            # Treat each snapshot as an independent recovery unit. A malformed
            # entry from a custom/legacy store must not prevent later valid
            # missions from being restored after restart.
            try:
                if not isinstance(item, dict):
                    raise TypeError("snapshot record must be a mapping")
                raw_mission = item.get("mission")
                raw_plan = item.get("plan")
                if not isinstance(raw_mission, CompanyMission):
                    raise TypeError("snapshot mission must be a CompanyMission")
                if not isinstance(raw_plan, MissionPlan):
                    raise TypeError("snapshot plan must be a MissionPlan")
                raw_mission_id = raw_mission.id
                mission_id = _durable_identity_text(raw_mission_id)
                if not mission_id or mission_id != raw_mission_id:
                    import logging

                    logging.getLogger(__name__).error(
                        "Skipping pending factory snapshot with invalid mission identity"
                    )
                    continue
                if mission_id in known_ids:
                    continue
                project = FactoryProject(**item)
                # Track whether recovery changes persisted snapshot state. If
                # sanitization or counter normalization is required, never queue
                # the item unless the repaired snapshot can be durably written.
                original_attempts = project.attempts
                original_stages_executed = project.stages_executed
                original_mission = project.mission.model_dump()
                original_plan = project.plan.model_dump()
                original_last_error = project.last_error
                original_retry_feedback = project.retry_feedback
                snapshot_needs_persist = False
                # Legacy snapshots predate strict counter validation. Normalize
                # counters before comparisons or queue scheduling can consume them.
                # Legacy/corrupt snapshots must not restore unbounded counters.
                # In particular, a huge attempts value can bypass retry budgets
                # and a huge stage count can poison dashboard/economics metrics.
                max_recovered_counter = 1_000_000
                for counter_name in ("attempts", "stages_executed"):
                    try:
                        counter = max(
                            0,
                            min(
                                max_recovered_counter,
                                int(getattr(project, counter_name)),
                            ),
                        )
                    except (TypeError, ValueError, OverflowError):
                        counter = 0
                    setattr(project, counter_name, counter)
                snapshot_needs_persist = (
                    project.attempts != original_attempts
                    or project.stages_executed != original_stages_executed
                )
            except Exception:
                # Snapshot stores may return legacy objects that bypassed model
                # validation or raise while exposing nested fields. Isolate each
                # record so one malformed entry cannot abort healthy recovery.
                import logging

                logging.getLogger(__name__).error(
                    "Skipping malformed pending factory snapshot"
                )
                continue
            # Older snapshots may predate write-time redaction. Sanitize text
            # before any restored mission or plan can be reused by an agent.
            # Keep sanitation inside the per-snapshot recovery boundary: legacy
            # model_copy payloads can bypass validation and contain malformed
            # nested values even when FactoryProject itself was constructed.
            try:
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
                snapshot_needs_persist = snapshot_needs_persist or (
                    project.mission.model_dump() != original_mission
                    or project.plan.model_dump() != original_plan
                    or project.last_error != original_last_error
                    or project.retry_feedback != original_retry_feedback
                )
            except Exception:
                # Sanitization traverses nested legacy plan data; keep failures
                # scoped to this record rather than aborting the restore pass.
                import logging

                logging.getLogger(__name__).error(
                    "Skipping malformed pending factory snapshot"
                )
                continue
            # Durable job stores are an independent recovery dependency. A
            # single corrupt/unavailable record must not abort restoration of
            # unrelated pending missions. Fail closed for this snapshot: if its
            # lifecycle cannot be verified, do not resurrect it from the older
            # project snapshot.
            try:
                job = self._load_job(project.mission.id)
            except Exception:
                import logging

                logging.getLogger(__name__).error(
                    "Unable to load durable mission job; skipping pending factory snapshot"
                )
                continue
            # A corrupt durable row may be indexed under its own mismatched ID,
            # so lookup by snapshot ID can return None even though a conflicting
            # row embeds this mission. Detect that conflict before trusting the
            # legacy snapshot as a standalone source of truth.
            if job is None and self.job_store is not None:
                list_all_jobs = getattr(self.job_store, "list_all", None)
                if not callable(list_all_jobs):
                    import logging

                    logging.getLogger(__name__).error(
                        "Durable job store cannot enumerate identities; skipping pending factory snapshot"
                    )
                    # A store that cannot enumerate identities is just as
                    # unverifiable as a failed scan: do not trust stale snapshot
                    # state as standalone truth.
                    continue
                try:
                    conflicting_jobs = list(list_all_jobs())
                except Exception:
                    import logging

                    logging.getLogger(__name__).error(
                        "Unable to verify durable mission identity; skipping pending factory snapshot"
                    )
                    # The snapshot cannot be trusted as standalone state when
                    # durable identity reconciliation is unavailable.
                    continue
                identity_index_valid = True
                seen_durable_ids: set[str] = set()
                seen_embedded_ids: set[str] = set()
                for candidate in conflicting_jobs:
                    try:
                        embedded_id = _durable_identity_text(candidate.mission.id)
                        durable_id = _durable_identity_text(candidate.id)
                    except (AttributeError, TypeError, ValueError):
                        import logging

                        logging.getLogger(__name__).error(
                            "Durable mission identity index contains an unreadable record; skipping pending snapshot"
                        )
                        identity_index_valid = False
                        break
                    if not embedded_id or not durable_id:
                        import logging

                        logging.getLogger(__name__).error(
                            "Durable mission identity index contains an empty identity; skipping pending snapshot"
                        )
                        identity_index_valid = False
                        break
                    # Recovery requires a one-to-one identity mapping. Duplicate
                    # keys or embedded mission IDs make the durable index ambiguous,
                    # even if one duplicate happens not to match this snapshot.
                    if (
                        durable_id in seen_durable_ids
                        or embedded_id in seen_embedded_ids
                    ):
                        import logging

                        logging.getLogger(__name__).error(
                            "Durable mission identity index contains duplicate identities; skipping pending snapshot"
                        )
                        identity_index_valid = False
                        break
                    seen_durable_ids.add(durable_id)
                    seen_embedded_ids.add(embedded_id)
                    # Either side of the identity pair can be corrupt:
                    # a row may claim this embedded mission under another key,
                    # or occupy this key while embedding a different mission.
                    if (embedded_id == project.mission.id) != (
                        durable_id == project.mission.id
                    ):
                        import logging

                        logging.getLogger(__name__).error(
                            "Skipping pending snapshot with mismatched durable mission identity"
                        )
                        job = candidate
                        break
                if not identity_index_valid:
                    continue
            if job is not None:
                # Validate the durable record for snapshot-backed recovery too.
                # The orphaned-job path already checks these invariants; without
                # the same gate here, a corrupt durable record could let an old
                # snapshot resurrect work under an invalid identity or status.
                try:
                    job_status = MissionJobStatus(job.status)
                    job_id = _durable_identity_text(job.id)
                    embedded_mission_id = _durable_identity_text(job.mission.id)
                except (AttributeError, TypeError, ValueError):
                    import logging

                    logging.getLogger(__name__).error(
                        "Skipping pending snapshot with invalid durable mission job"
                    )
                    continue
                if (
                    not job_id
                    or job_id != project.mission.id
                    or embedded_mission_id != project.mission.id
                ):
                    import logging

                    logging.getLogger(__name__).error(
                        "Skipping pending snapshot with mismatched durable mission identity"
                    )
                    continue
                normalized_attempts = _bounded_job_attempts(job.attempts)
                attempts_changed = normalized_attempts != job.attempts
                job = job.model_copy(
                    update={"status": job_status, "attempts": normalized_attempts}
                )
                safe_job_mission = self._safe_mission(job.mission)
                safe_job_plan = self._safe_plan(job.plan)
                if (
                    attempts_changed
                    or safe_job_mission.model_dump() != job.mission.model_dump()
                    or safe_job_plan.model_dump() != job.plan.model_dump()
                ):
                    job = job.model_copy(
                        update={"mission": safe_job_mission, "plan": safe_job_plan}
                    )
                    try:
                        self._save_job(job)
                    except Exception:
                        import logging

                        logging.getLogger(__name__).error(
                            "Unable to persist sanitized mission job during restore"
                        )
                        continue
            # The project store can contain a stale snapshot if shutdown or
            # cancellation happened between persistence operations. Durable
            # terminal job state wins: never resurrect completed, failed,
            # blocked, or cancelled work into the active queue.
            # When a durable row exists, its validated lifecycle is authoritative.
            # Without one, only pending snapshots are eligible for recovery; terminal
            # or unknown snapshot states must not be silently re-enqueued.
            if job is None and project.status not in {"queued", "running"}:
                import logging

                logging.getLogger(__name__).error(
                    "Skipping pending factory snapshot with ineligible lifecycle status"
                )
                continue
            if job is not None and job.status == MissionJobStatus.QUEUED:
                project.status = "queued"
            # Reserve an ID only after the snapshot and its durable lifecycle
            # have passed validation. A malformed earlier duplicate must not
            # shadow a later valid snapshot for the same mission.
            if job is not None and job.status in {
                MissionJobStatus.COMPLETED,
                MissionJobStatus.FAILED,
                MissionJobStatus.BLOCKED,
                MissionJobStatus.CANCELLED,
            }:
                known_ids.add(project.mission.id)
                delete_many = getattr(self.store, "delete_many", None)
                if callable(delete_many):
                    try:
                        delete_many({project.mission.id})
                    except Exception:
                        import logging

                        logging.getLogger(__name__).error(
                            "Unable to delete terminal mission snapshot during restore"
                        )
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
                    try:
                        self._save(project)
                    except Exception:
                        import logging

                        logging.getLogger(__name__).error(
                            "Unable to refresh queued mission snapshot during restore"
                        )

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
                try:
                    self._save_job(recovered_job)
                except Exception:
                    import logging

                    logging.getLogger(__name__).error(
                        "Unable to persist recovered running mission; skipping snapshot"
                    )
                    continue

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
            try:
                self._save(project)
            except Exception:
                import logging

                logging.getLogger(__name__).error(
                    "Unable to persist restored mission snapshot"
                )
                if snapshot_needs_persist:
                    # Do not enqueue legacy state that still contains secrets
                    # or unbounded counters because its repair could not be saved.
                    continue
            known_ids.add(project.mission.id)
            self.queue.append(project)
            restored += 1

        # The durable job table is authoritative for lifecycle state, but a
        # crash can occur after writing a job and before writing its project
        # snapshot. Recover those orphaned jobs so they do not disappear on
        # restart. This is optional for custom stores that only implement get.
        list_all = getattr(self.job_store, "list_all", None)
        if callable(list_all):
            # Reuse the exact list that passed identity preflight. A store may
            # change between calls (or return a different view during concurrent
            # writes); recovery must not enqueue records from an unvalidated view.
            durable_jobs = durable_jobs_snapshot
            if durable_jobs is None:
                import logging

                logging.getLogger(__name__).error(
                    "Skipping orphaned durable recovery without a validated job snapshot"
                )
                durable_jobs = []
            # Orphan recovery must validate the entire enumerated identity
            # index before enqueueing any record. Otherwise a duplicate can be
            # skipped by snapshot reconciliation but resurrected here as an orphan.
            durable_ids: set[str] = set()
            embedded_ids: set[str] = set()
            identity_index_valid = True
            for candidate in durable_jobs:
                try:
                    durable_id = _durable_identity_text(candidate.id)
                    embedded_id = _durable_identity_text(candidate.mission.id)
                except Exception:
                    # The identity index is a single trust boundary: if even one
                    # row cannot be read, uniqueness cannot be established safely.
                    identity_index_valid = False
                    break
                if (
                    not durable_id
                    or not embedded_id
                    or durable_id != embedded_id
                    or durable_id in durable_ids
                    or embedded_id in embedded_ids
                ):
                    identity_index_valid = False
                    break
                durable_ids.add(durable_id)
                embedded_ids.add(embedded_id)
            if not identity_index_valid:
                import logging

                logging.getLogger(__name__).error(
                    "Skipping orphaned durable mission recovery because identity index is ambiguous"
                )
                return restored
            for job in durable_jobs:
                try:
                    # Durable job identity is the queue's idempotency key. A
                    # corrupt/mismatched record must not enqueue one mission
                    # under a different ID and then duplicate it on every restore.
                    mission_id = str(job.id).strip()
                    mission = job.mission
                    if not mission_id or mission_id != str(mission.id).strip():
                        import logging

                        logging.getLogger(__name__).error(
                            "Skipping durable mission job with mismatched identity"
                        )
                        continue
                    if mission_id in known_ids:
                        continue
                    # Only explicitly eligible lifecycle states may enter the
                    # active queue. Unknown future/corrupt states fail closed.
                    try:
                        status = MissionJobStatus(job.status)
                    except (TypeError, ValueError):
                        import logging

                        logging.getLogger(__name__).error(
                            "Skipping durable mission job with invalid lifecycle status"
                        )
                        continue
                    if status not in {
                        MissionJobStatus.QUEUED,
                        MissionJobStatus.RUNNING,
                    }:
                        continue
                    normalized_attempts = _bounded_job_attempts(job.attempts)
                    attempts_changed = normalized_attempts != job.attempts
                    job = job.model_copy(
                        update={"status": status, "attempts": normalized_attempts}
                    )
                    safe_mission = self._safe_mission(job.mission)
                    safe_plan = self._safe_plan(job.plan)
                    recovery_state_changed = (
                        attempts_changed
                        or safe_mission.model_dump() != job.mission.model_dump()
                        or safe_plan.model_dump() != job.plan.model_dump()
                    )
                    job = job.model_copy(
                        update={"mission": safe_mission, "plan": safe_plan}
                    )
                    if (
                        job.status == MissionJobStatus.QUEUED
                        and recovery_state_changed
                    ):
                        try:
                            self._save_job(job)
                        except Exception:
                            import logging

                            logging.getLogger(__name__).error(
                                "Unable to persist normalized queued mission recovery state"
                            )
                            continue
                    if job.status == MissionJobStatus.RUNNING:
                        job = recover_running_job(job)
                        try:
                            self._save_job(job)
                        except Exception:
                            import logging

                            logging.getLogger(__name__).error(
                                "Unable to persist orphaned running mission recovery"
                            )
                            continue
                    project = FactoryProject(
                        mission=job.mission,
                        plan=job.plan,
                        status="queued",
                        attempts=max(0, int(job.attempts)),
                    )
                    try:
                        self._save(project)
                    except Exception:
                        import logging

                        logging.getLogger(__name__).error(
                            "Unable to persist orphaned durable mission snapshot; keeping it in memory"
                        )
                    self.queue.append(project)
                    known_ids.add(mission_id)
                    restored += 1
                except Exception:
                    # Custom stores and legacy model_copy payloads can raise
                    # arbitrary exceptions while nested mission/plan fields are
                    # inspected or sanitized. Contain them to this job so a
                    # malformed row cannot abort recovery of later healthy jobs.
                    import logging

                    logging.getLogger(__name__).error(
                        "Skipping malformed orphaned durable mission job"
                    )
                    continue
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
        # Persist the project snapshot before exposing it to the worker queue.
        # If persistence fails, callers can retry enqueue without a ghost in-memory
        # entry or a duplicate-lifecycle error caused by partially published work.
        self._save(project)
        # Preserve FIFO ordering: the first submitted mission must execute first.
        # A terminal failure is recorded per mission; it must not discard unrelated work.
        self.queue.append(project)
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

    def reconcile_mission(self, mission_id: str, *, repair: bool = False) -> dict[str, Any]:
        """Compare durable job, persisted snapshot, and in-memory queue.

        By default this is read-only. Repair is deliberately limited to the
        unambiguous case where a durable QUEUED job has no in-memory copy and
        the factory is idle. Conflicting or incomplete evidence is reported,
        never guessed away.
        """
        if not isinstance(repair, bool):
            raise ValueError("repair must be a boolean")
        job = self._load_job(mission_id)
        if job is None:
            return {
                "mission_id": mission_id,
                "consistent": False,
                "repair_attempted": False,
                "discrepancies": ["durable_job_missing"],
                "recommended_action": "inspect_durable_job_store",
            }

        queued = [item for item in self.queue if item.mission.id == mission_id]
        active_id = self._active_project.mission.id if self._active_project else None
        snapshots: list[dict[str, Any]] = []
        snapshot_error = False
        if self.store is not None:
            try:
                for item in self.store.load_pending():
                    if isinstance(item, dict):
                        mission = item.get("mission")
                        if getattr(mission, "id", None) == mission_id:
                            snapshots.append(item)
            except Exception:
                snapshot_error = True

        discrepancies: list[str] = []
        if snapshot_error:
            discrepancies.append("project_snapshot_store_unavailable")
        if len(snapshots) > 1:
            discrepancies.append("duplicate_project_snapshots")
        if len(queued) > 1:
            discrepancies.append("duplicate_in_memory_queue_entries")
        if job.status == MissionJobStatus.QUEUED and not queued:
            discrepancies.append("durable_queued_job_missing_from_memory_queue")
        if job.status != MissionJobStatus.QUEUED and queued:
            discrepancies.append("memory_queue_conflicts_with_durable_status")
        if job.status == MissionJobStatus.RUNNING and active_id != mission_id:
            discrepancies.append("durable_running_job_has_no_matching_active_worker")
        if active_id == mission_id and job.status != MissionJobStatus.RUNNING:
            discrepancies.append("active_worker_conflicts_with_durable_status")
        if snapshots:
            snapshot = snapshots[0]
            raw_plan = snapshot.get("plan")
            if not isinstance(raw_plan, MissionPlan):
                discrepancies.append("project_snapshot_plan_invalid")
            elif raw_plan.model_dump() != job.plan.model_dump():
                discrepancies.append("project_snapshot_plan_differs_from_durable_job")
            if snapshot.get("status") != job.status.value:
                discrepancies.append("project_snapshot_status_differs_from_durable_job")
        elif self.store is not None and not snapshot_error:
            discrepancies.append("project_snapshot_missing")

        repair_attempted = False
        if repair and not snapshot_error and not discrepancies:
            # No work needed; preserve idempotency.
            pass
        elif repair:
            repair_attempted = True
            if self._running or self._active_project is not None:
                raise RuntimeError("Cannot reconcile recovery state while the factory worker is active")
            # Only one safe repair is permitted: rehydrate a missing in-memory
            # queue entry from a single, valid, durably QUEUED job, with no
            # conflicting snapshot evidence.
            safe_to_rehydrate = (
                job.status == MissionJobStatus.QUEUED
                and not queued
                and not snapshot_error
                and len(snapshots) <= 1
                and not any(
                    item in discrepancies
                    for item in (
                        "duplicate_project_snapshots",
                        "duplicate_in_memory_queue_entries",
                        "project_snapshot_plan_invalid",
                        "project_snapshot_plan_differs_from_durable_job",
                        "project_snapshot_status_differs_from_durable_job",
                        "memory_queue_conflicts_with_durable_status",
                        "durable_running_job_has_no_matching_active_worker",
                        "active_worker_conflicts_with_durable_status",
                    )
                )
            )
            if safe_to_rehydrate:
                project = FactoryProject(
                    mission=job.mission,
                    plan=job.plan.model_copy(deep=True),
                    status="queued",
                    attempts=job.attempts,
                )
                self._save(project)
                self.queue.append(project)
                discrepancies = [
                    item for item in discrepancies
                    if item != "durable_queued_job_missing_from_memory_queue"
                    and item != "project_snapshot_missing"
                ]
                if self.store is not None and not snapshots:
                    # _save wrote the missing snapshot; confirm the next inspect.
                    discrepancies.append("snapshot_repair_written_verification_pending")
            elif discrepancies:
                self._audit(
                    mission_id,
                    "MISSION_RECONCILIATION_WITHHELD",
                    "Automatic reconciliation withheld because durable state is ambiguous",
                    job.status.value,
                    {"discrepancies": discrepancies},
                )

        consistent = not discrepancies
        recommended_action = (
            "none" if consistent
            else "inspect_store_outage" if snapshot_error
            else "inspect_duplicate_or_conflicting_state"
            if any("duplicate" in item or "conflicts" in item or "differs" in item for item in discrepancies)
            else "restart_or_restore_factory"
            if "durable_running_job_has_no_matching_active_worker" in discrepancies
            else "reconcile_durable_queued_job"
        )
        return {
            "mission_id": mission_id,
            "durable_status": job.status.value,
            "snapshot_count": len(snapshots),
            "queue_entry_count": len(queued),
            "active_worker_matches": active_id == mission_id,
            "consistent": consistent,
            "repair_attempted": repair_attempted,
            "discrepancies": discrepancies,
            "recommended_action": recommended_action,
        }

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
        # Resume from the last valid checkpoint instead of replaying completed
        # stages. Failed/in-flight stages are reset, and any completed downstream
        # stage whose prerequisites are no longer complete is invalidated.
        plan = resume_failed_plan(queued.plan)
        queued = queued.model_copy(update={"plan": plan})
        self._save_job(queued)
        project = FactoryProject(
            mission=queued.mission,
            plan=plan,
            attempts=queued.attempts,
            retry_feedback=(self._safe_error_detail(retry_feedback)[:2000] if retry_feedback else None),
        )
        self._save(project)
        # Mutate the in-memory queue only after durable job and project writes
        # succeed. A transient store failure must not silently drop a queued copy.
        self.queue = [item for item in self.queue if item.mission.id != mission_id]
        self.queue.append(project)
        self._audit(mission_id, "MISSION_REQUEUED", queued.message, queued.status.value)
        return queued

    def recover_mission(self, mission_id: str, action: str) -> dict[str, Any]:
        """Execute an explicit, guarded recovery action against durable mission state.

        Supported actions are inspect, resume (already-queued work only), and
        retry (failed/blocked work only). Never guess that a running mission is
        safe to restart.
        """
        normalized_action = str(action).strip().lower()
        if normalized_action not in {"inspect", "resume", "retry"}:
            raise ValueError("Recovery action must be one of: inspect, resume, retry")
        job = self._load_job(mission_id)
        if job is None:
            raise KeyError(mission_id)

        if normalized_action == "inspect":
            return {
                "mission_id": mission_id,
                "status": job.status.value,
                "action": "inspect",
                "changed": False,
                "recommended_action": (
                    "retry" if job.status in {MissionJobStatus.FAILED, MissionJobStatus.BLOCKED}
                    else "resume" if job.status == MissionJobStatus.QUEUED
                    else "none" if job.status == MissionJobStatus.COMPLETED
                    else "inspect_worker_state"
                ),
            }

        if self._running or self._active_project is not None:
            raise RuntimeError("Cannot recover a mission while the factory worker is active")

        if normalized_action == "retry":
            if job.status not in {MissionJobStatus.FAILED, MissionJobStatus.BLOCKED}:
                raise ValueError(
                    f"Mission '{mission_id}' cannot be retried from '{job.status.value}'"
                )
            queued = self.retry(mission_id)
            self._audit(
                mission_id,
                "MISSION_RECOVERY_ACTION",
                "Explicit recovery action retried a failed mission",
                queued.status.value,
                {"action": "retry"},
            )
            return {
                "mission_id": mission_id,
                "status": queued.status.value,
                "action": "retry",
                "changed": True,
                "recommended_action": "run_queued_mission",
            }

        if job.status != MissionJobStatus.QUEUED:
            raise ValueError(
                f"Mission '{mission_id}' cannot be resumed from '{job.status.value}'; "
                "only durably queued missions can be rehydrated"
            )
        existing = next((item for item in self.queue if item.mission.id == mission_id), None)
        if existing is not None:
            return {
                "mission_id": mission_id,
                "status": job.status.value,
                "action": "resume",
                "changed": False,
                "recommended_action": "already_queued",
            }

        # Durable QUEUED status authorizes reconstruction of in-memory work.
        # Persist the project snapshot before publishing it to the queue.
        project = FactoryProject(
            mission=job.mission,
            plan=job.plan.model_copy(deep=True),
            status="queued",
            attempts=job.attempts,
        )
        self._save(project)
        self.queue.append(project)
        self._audit(
            mission_id,
            "MISSION_RECOVERY_ACTION",
            "Explicit recovery action rehydrated a durably queued mission",
            job.status.value,
            {"action": "resume"},
        )
        return {
            "mission_id": mission_id,
            "status": job.status.value,
            "action": "resume",
            "changed": True,
            "recommended_action": "run_queued_mission",
        }

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
        if (
            isinstance(max_retries, bool)
            or not isinstance(max_retries, int)
            or max_retries < 0
        ):
            raise ValueError("max_retries must be a non-negative integer")
        if max_stages is not None and (
            isinstance(max_stages, bool)
            or not isinstance(max_stages, int)
            or max_stages < 0
        ):
            raise ValueError("max_stages must be a non-negative integer or None")
        timeout = self.execution_timeout_seconds
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError(
                "execution_timeout_seconds must be a finite positive number"
            )
        # A zero-stage budget is an intentional no-op, not an execution attempt.
        # Leave the mission queued so a later run with a positive budget can resume it.
        # A factory instance may be driven by both the background worker and
        # a direct run_next call. Reject overlapping execution before inspecting
        # or mutating the queue: otherwise two coroutines can claim different
        # queue entries and run missions concurrently.
        if self._active_project is not None:
            raise RuntimeError(
                "Factory execution is already active for mission "
                f"'{self._active_project.mission.id}'"
            )

        if max_stages == 0 or not self.queue:
            return None

        now = time.time()
        eligible_index = next(
            (index for index, item in enumerate(self.queue)
             if item.retry_not_before_epoch <= now),
            None,
        )
        if eligible_index is None:
            return None

        # The durable job is the idempotency authority. A stale in-memory queue
        # entry must never re-run a mission that another worker has already
        # claimed or that has reached a terminal lifecycle state.
        queued_candidate = self.queue[eligible_index]
        durable_job = self._load_job(queued_candidate.mission.id)
        if durable_job is not None and durable_job.status != MissionJobStatus.QUEUED:
            self.queue.pop(eligible_index)
            return None

        # Keep the project in the FIFO queue until its startup state is durable.
        # A failed snapshot/job/audit write must not consume an attempt or strand
        # the mission outside the queue before execution's recovery boundary begins.
        project = self.queue[eligible_index]
        previous_status = project.status
        previous_attempts = project.attempts
        previous_error = project.last_error
        previous_retry_not_before = project.retry_not_before_epoch
        self._active_project = project
        self._last_autonomous_result = None
        project.status = "running"
        project.worker_started_at = datetime.now(UTC)
        project.last_progress_at = project.worker_started_at
        project.progress_updates = 0
        project.retry_not_before_epoch = 0.0
        project.attempts += 1
        project.last_error = None
        try:
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
        except Exception:
            # Roll back the in-memory transition and make a best-effort repair of
            # any durable store that may have accepted only part of startup.
            project.status = previous_status
            project.attempts = previous_attempts
            project.last_error = previous_error
            project.retry_not_before_epoch = previous_retry_not_before
            self._active_project = None
            self._last_autonomous_result = None
            try:
                self._save(project)
            except Exception:
                pass
            try:
                current_job = self._load_job(project.mission.id)
                if current_job is not None and current_job.status == MissionJobStatus.RUNNING:
                    self._save_job(
                        current_job.model_copy(
                            update={
                                "status": MissionJobStatus.QUEUED,
                                "attempts": previous_attempts,
                                "plan": project.plan,
                                "message": f"Factory startup interrupted; mission remains queued: {project.mission.name}",
                                "updated_at": datetime.now(UTC),
                            }
                        )
                    )
            except Exception:
                pass
            raise

        # Dequeue only after all startup persistence and audit operations succeed.
        self.queue.pop(eligible_index)
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
            # Cancellation bypasses ordinary Exception handling. Never enqueue
            # a second in-process copy until the interrupted state has been
            # persisted; if durable recovery writes fail, leave the job for the
            # startup recovery path rather than risking duplicate execution.
            project.status = "queued"
            project.last_error = (
                "Factory execution cancelled; interrupted work requires safe resume."
            )
            project.plan = recover_running_plan(project.plan)
            durable_recovery_ready = True
            try:
                self._save(project)
            except Exception:
                durable_recovery_ready = False
                import logging

                logging.getLogger(__name__).exception(
                    "Unable to persist cancelled mission snapshot; leaving it out of the in-process queue"
                )
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
                            f"Execution interrupted; mission requires safe resume: {project.mission.name}",
                        )
                    )
            except Exception:
                durable_recovery_ready = False
                import logging

                logging.getLogger(__name__).exception(
                    "Unable to persist cancelled mission job; leaving it out of the in-process queue"
                )
            try:
                self.orchestrator.stop()
            except Exception:
                pass
            if durable_recovery_ready:
                if not any(item.mission.id == project.mission.id for item in self.queue):
                    self.queue.insert(0, project)
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
            else:
                # Do not claim this is safely queued. The durable RUNNING job,
                # if present, is recoverable on restart; operator diagnostics
                # must explain why automatic in-process retry was withheld.
                project.last_error = (
                    "Execution was cancelled, but recovery persistence failed. "
                    "Automatic retry was withheld to prevent duplicate execution."
                )
                try:
                    self._audit(
                        project.mission.id,
                        "MISSION_CANCELLATION_RECOVERY_FAILED",
                        project.last_error,
                        MissionJobStatus.RUNNING.value,
                        {"attempt": project.attempts, "recovered_for_resume": False},
                    )
                except Exception:
                    pass
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
            failure_class = classify_failure(project.last_error)
            if failure_class == FailureClass.NON_RETRYABLE:
                project.status = "blocked"
                self.orchestrator.stop()
                self._transition_job(
                    project,
                    MissionJobStatus.BLOCKED,
                    f"Project blocked by non-retryable failure: {project.mission.name}",
                )
                event_type = "FACTORY_PROJECT_BLOCKED_NON_RETRYABLE"
            elif project.attempts <= max_retries and max_retries > 0:
                project.status = "queued"
                self._reset_for_retry(project, reset_completed=True)
                self._apply_retry_backoff(project)
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
            elif classify_failure(project.last_error) == FailureClass.NON_RETRYABLE:
                project.status = "blocked"
                self.orchestrator.block(project.last_error)
                self._transition_job(
                    project,
                    MissionJobStatus.BLOCKED,
                    f"Project blocked by non-retryable failure: {project.mission.name}",
                )
                event_type = "FACTORY_PROJECT_BLOCKED_NON_RETRYABLE"
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
                or (
                    max_stages is None
                    and any(step.status != "completed" for step in project.plan.steps)
                )
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
        stage_counts: dict[str, int] = {}
        stage_timeline = []
        for step in project.plan.steps:
            status = str(getattr(step.status, "value", step.status))
            stage_counts[status] = stage_counts.get(status, 0) + 1
            stage_timeline.append({
                "stage": step.stage.value,
                "status": status,
                "attempts": max(0, int(getattr(step, "attempts", 0) or 0)),
                "detail": self._safe_error_detail(str(step.detail)) if step.detail else None,
            })
        audit_metadata = {
            "attempt": project.attempts,
            "stages_executed": project.stages_executed,
            "orchestrator_status": self.orchestrator.state.status.value,
            "execution_mode": (
                "autonomous" if self.autonomous_runner is not None else "agent_pipeline"
            ),
            "stage_counts": stage_counts,
            "stage_timeline": stage_timeline,
            "retry_decision": (
                "retry_queued" if "RETRY_QUEUED" in event_type
                else "blocked" if "BLOCKED" in event_type
                else "paused" if "PAUSED" in event_type
                else "completed" if "COMPLETED" in event_type
                else "other"
            ),
            "recovery_diagnostics": build_recovery_diagnostics(
                status=project.status,
                last_error=project.last_error,
                attempts=project.attempts,
                steps=project.plan.steps,
                queue_depth=len(self.queue),
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

    def _apply_retry_backoff(self, project: FactoryProject) -> None:
        """Set a bounded exponential cooldown for a failed automatic retry."""
        delay_seconds = min(0.5 * (2 ** min(max(project.attempts - 1, 0), 6)), 30.0)
        project.retry_not_before_epoch = time.time() + delay_seconds

    def _requeue_for_fairness(self, project: FactoryProject) -> None:
        """Move a retry to the tail, removing stale duplicate queue entries."""
        # A recovery/cleanup path may leave the same mission in the queue already.
        # Merely avoiding a duplicate would preserve its old position and let a
        # retry jump ahead of missions that have waited longer.
        mission_id = project.mission.id
        self.queue = [item for item in self.queue if item.mission.id != mission_id]
        self.queue.append(project)

    @staticmethod
    def _safe_error_detail(value: str) -> str:
        """Redact and bound exception text before persisting it to mission state."""
        return redact_sensitive_text(str(value))[:4000]

    def _contain_unexpected_worker_error(
        self, project: FactoryProject, exc: Exception
    ) -> None:
        """Best-effort terminalize a mission if an error escapes run_next cleanup."""
        if project.status not in {"blocked", "cancelled"}:
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
        # Validate every run budget before changing worker state or touching the queue.
        if max_projects is not None and (
            isinstance(max_projects, bool)
            or not isinstance(max_projects, int)
            or max_projects < 0
        ):
            raise ValueError("max_projects must be a non-negative integer or None")
        if max_stages is not None and (
            isinstance(max_stages, bool)
            or not isinstance(max_stages, int)
            or max_stages < 0
        ):
            raise ValueError("max_stages must be a non-negative integer or None")
        if (
            isinstance(max_retries, bool)
            or not isinstance(max_retries, int)
            or max_retries < 0
        ):
            raise ValueError("max_retries must be a non-negative integer")
        # A zero-project budget is an intentional no-op: do not acquire the
        # worker lock or emit a run-completed event when no work was requested.
        if max_projects == 0:
            return []
        if self._running:
            raise RuntimeError("Factory is already running")
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
                    if max_stages == 0:
                        break
                    if self.queue:
                        now = time.time()
                        if any(item.retry_not_before_epoch <= now for item in self.queue):
                            continue
                        deadlines = [
                            item.retry_not_before_epoch
                            for item in self.queue
                            if item.retry_not_before_epoch > now
                        ]
                        if deadlines:
                            await asyncio.sleep(min(max(min(deadlines) - now, 0.01), 1.0))
                            continue
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
                output_type=(
                    "autonomous_project"
                    if pipeline_result is not None
                    else "factory_project"
                ),
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
        """Persist authoritative progress, refresh heartbeat, and record a timeline breadcrumb."""
        project.last_progress_at = datetime.now(UTC)
        project.progress_updates += 1
        # The durable job remains authoritative during restore: write it before
        # publishing the matching project snapshot.
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
        self._save(project)
        timeline = [
            {
                "stage": step.stage.value,
                "status": str(getattr(step.status, "value", step.status)),
                "attempts": max(0, int(getattr(step, "attempts", 0) or 0)),
                "detail": self._safe_error_detail(str(step.detail)) if step.detail else None,
            }
            for step in project.plan.steps
        ]
        self._audit(
            project.mission.id,
            "MISSION_PROGRESS_SNAPSHOT",
            f"Persisted mission progress: {project.mission.name}",
            job.status.value if job is not None else None,
            {
                "attempt": project.attempts,
                "stages_executed": project.stages_executed,
                "stage_timeline": timeline,
                "progress_updates": project.progress_updates,
                "qa_status": getattr(getattr(project.plan, "qa_status", None), "value", getattr(project.plan, "qa_status", None)),
                "security_status": getattr(getattr(project.plan, "security_status", None), "value", getattr(project.plan, "security_status", None)),
            },
        )

    def worker_health(self, stale_after_seconds: float | None = None) -> dict[str, Any]:
        """Return a read-only worker heartbeat snapshot; stale detection never cancels work."""
        threshold = (
            max(1.0, float(self.execution_timeout_seconds))
            if stale_after_seconds is None
            else stale_after_seconds
        )
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold)
            or threshold <= 0
        ):
            raise ValueError("stale_after_seconds must be a finite positive number")
        project = self._active_project
        now = datetime.now(UTC)
        last = project.last_progress_at if project is not None else None
        age = max(0.0, (now - last).total_seconds()) if last is not None else None
        if project is None:
            status = "idle"
        elif age is not None and age > threshold:
            status = "stale"
        else:
            status = "healthy"
        return {
            "status": status,
            "active_mission_id": project.mission.id if project is not None else None,
            "active_mission_name": project.mission.name if project is not None else None,
            "worker_started_at": project.worker_started_at.isoformat() if project and project.worker_started_at else None,
            "last_progress_at": last.isoformat() if last else None,
            "heartbeat_age_seconds": age,
            "stale_after_seconds": float(threshold),
            "progress_updates": project.progress_updates if project is not None else 0,
            "queue_depth": len(self.queue),
            "diagnostic": (
                "No mission is currently active."
                if project is None
                else "Worker progress heartbeat is stale; inspect before restarting. Work was not cancelled or requeued."
                if status == "stale"
                else "Active mission has a recent progress heartbeat."
            ),
        }


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
