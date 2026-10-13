from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, create_engine, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.company.audit import MissionAuditEntry
from src.company.mission_controller.models import MissionPlan
from src.company.mission_jobs import (
    MissionJob,
    MissionJobStatus,
    recover_running_job,
    recover_running_plan,
)
from src.company.models.contracts import CompanyMission
from src.company.project_outputs import ProjectOutputManifest
from src.config.settings import settings
from src.security.redaction import redact_sensitive_text, redact_sensitive_value
from src.db.base import Base


def _safe_mission(mission: CompanyMission) -> CompanyMission:
    """Normalize legacy persisted mission text before it reaches callers or agents."""
    def safe_text(value: str, limit: int) -> str:
        return redact_sensitive_text(str(value))[:limit]
    return mission.model_copy(update={
        "name": safe_text(mission.name, 500),
        "objective": safe_text(mission.objective, 8000),
        "constraints": [safe_text(value, 2000) for value in mission.constraints],
    })


def _safe_plan(plan: MissionPlan) -> MissionPlan:
    """Bound and redact free text in legacy plans loaded directly from storage."""
    safe = plan.model_copy(deep=True)
    def safe_text(value: str, limit: int) -> str:
        return redact_sensitive_text(str(value))[:limit]
    for name, limit in (("name", 500), ("objective", 8000), ("qa_status", 120),
                        ("qa_evidence", 5200), ("security_status", 120),
                        ("security_summary", 1000), ("security_evidence", 2000)):
        value = getattr(safe, name, None)
        if isinstance(value, str):
            setattr(safe, name, safe_text(value, limit))
    safe.constraints = [safe_text(value, 2000) for value in safe.constraints]
    safe.acceptance_criteria = [safe_text(value, 4000) for value in safe.acceptance_criteria]
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


def _safe_factory_snapshot(project: FactoryProject) -> dict[str, Any]:
    """Normalize project snapshot content before it is written to durable storage."""
    mission = _safe_mission(project.mission)
    plan = _safe_plan(project.plan)
    status = redact_sensitive_text(str(project.status))[:32]
    return {
        "mission": mission.model_dump(mode="json"),
        "plan": plan.model_dump(mode="json"),
        "status": status,
        "stages_executed": max(0, int(project.stages_executed)),
        "attempts": max(0, int(project.attempts)),
    }


def _safe_job(job: MissionJob) -> MissionJob:
    """Normalize durable mission-job fields even when model_copy bypassed validators."""
    return job.model_copy(update={
        "mission": _safe_mission(job.mission),
        "plan": _safe_plan(job.plan),
        "message": redact_sensitive_text(str(job.message))[:4000],
        "attempts": max(0, int(job.attempts)),
    })


def _rewrite_safe_job_row(row: MissionJobRow, job: MissionJob) -> bool:
    """Rewrite normalized legacy mission-job fields so unsafe values do not persist."""
    mission = job.mission.model_dump(mode="json")
    plan = job.plan.model_dump(mode="json")
    changed = (
        row.mission != mission
        or row.plan != plan
        or row.message != job.message
        or row.attempts != job.attempts
    )
    if changed:
        row.mission = mission
        row.plan = plan
        row.message = job.message
        row.attempts = job.attempts
    return changed


def _bounded_audit_value(value: Any, *, depth: int = 0) -> Any:
    """Bound nested audit metadata so legacy records cannot grow without limit."""
    if depth >= 6:
        return "[TRUNCATED]" if value is not None else None
    if isinstance(value, str):
        return redact_sensitive_text(value)[:2000]
    if isinstance(value, dict):
        return {str(key)[:120]: _bounded_audit_value(item, depth=depth + 1) for key, item in list(value.items())[:100]}
    if isinstance(value, (list, tuple)):
        return [_bounded_audit_value(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_sensitive_text(str(value))[:500]


def _bounded_audit_limit(limit: int) -> int:
    """Clamp audit-history reads to a small, predictable page size."""
    return max(1, min(int(limit), 500))


def _safe_audit_entry(entry: MissionAuditEntry) -> MissionAuditEntry:
    """Redact and bound audit entries before durable writes and after legacy reads."""
    metadata = redact_sensitive_value(entry.metadata)
    return entry.model_copy(update={
        "id": redact_sensitive_text(entry.id)[:100],
        "mission_id": redact_sensitive_text(entry.mission_id)[:100],
        "event_type": redact_sensitive_text(entry.event_type)[:100],
        "message": redact_sensitive_text(entry.message)[:4000],
        "status": redact_sensitive_text(entry.status)[:80] if entry.status is not None else None,
        "metadata": _bounded_audit_value(metadata),
    })


def _safe_output_manifest(manifest: ProjectOutputManifest) -> ProjectOutputManifest:
    """Bound and redact durable project-output metadata on write and read."""
    def safe_text(value: str | None, limit: int) -> str | None:
        if value is None:
            return None
        return redact_sensitive_text(str(value))[:limit]

    return manifest.model_copy(update={
        "id": safe_text(manifest.id, 100),
        "mission_id": safe_text(manifest.mission_id, 100),
        "project_id": safe_text(manifest.project_id, 200),
        "name": safe_text(manifest.name, 500),
        "status": safe_text(manifest.status, 80),
        "output_type": safe_text(manifest.output_type, 100),
        "repository": safe_text(manifest.repository, 500),
        "product_url": safe_text(manifest.product_url, 1000),
        "github_message": safe_text(manifest.github_message, 2000),
        "memory_id": safe_text(manifest.memory_id, 100),
    })


if TYPE_CHECKING:
    from src.company.project_factory import FactoryProject


class FactoryProjectRow(Base):
    __tablename__ = "factory_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mission: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    stages_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectOutputRow(Base):
    __tablename__ = "project_outputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    output_type: Mapped[str] = mapped_column(String(64), nullable=False)
    repository: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_message: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    memory_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MissionJobRow(Base):
    __tablename__ = "mission_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mission: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(String(5000), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)



class MissionAuditRow(Base):
    __tablename__ = "mission_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(String(5000), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MissionJobStore:
    """Durable store for mission lifecycle jobs."""

    def __init__(self) -> None:
        url = settings.database_url.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg://",
        )
        self._engine = create_engine(url, pool_pre_ping=True)

    def save(self, job: MissionJob) -> None:
        job = _safe_job(job)
        with Session(self._engine) as session:
            row = session.get(MissionJobRow, job.id)
            values = {
                "mission": job.mission.model_dump(mode="json"),
                "plan": job.plan.model_dump(mode="json"),
                "status": getattr(job.status, "value", job.status),
                "message": job.message,
                "workspace_id": job.workspace_id,
                "attempts": job.attempts,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
            if row is None:
                session.add(MissionJobRow(id=job.id, **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            session.commit()

    def get(self, job_id: str) -> MissionJob | None:
        with Session(self._engine) as session:
            row = session.get(MissionJobRow, job_id)
            if row is None:
                return None
            job = _safe_job(MissionJob(
                id=row.id,
                mission=CompanyMission.model_validate(row.mission),
                plan=MissionPlan.model_validate(row.plan),
                status=MissionJobStatus(row.status),
                message=row.message,
                workspace_id=row.workspace_id,
                attempts=row.attempts,
                created_at=row.created_at,
                updated_at=row.updated_at,
            ))
            if _rewrite_safe_job_row(row, job):
                session.commit()
            return job

    def recover_running(self) -> list[MissionJob]:
        recovered: list[MissionJob] = []
        with Session(self._engine) as session:
            rows = session.scalars(
                select(MissionJobRow).where(MissionJobRow.status == MissionJobStatus.RUNNING.value)
            ).all()
            for row in rows:
                try:
                    job = _safe_job(MissionJob(
                        id=row.id,
                        mission=CompanyMission.model_validate(row.mission),
                        plan=MissionPlan.model_validate(row.plan),
                        status=MissionJobStatus(row.status),
                        message=row.message,
                        workspace_id=row.workspace_id,
                        attempts=row.attempts,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    ))
                    job = _safe_job(recover_running_job(job))
                except (TypeError, ValueError, OverflowError):
                    # A corrupt legacy job must not block recovery of other
                    # interrupted missions. Avoid logging untrusted row data.
                    logging.getLogger(__name__).error(
                        "Skipping malformed running mission-job snapshot"
                    )
                    continue
                # Recovery is also a durable write boundary: rewrite every
                # normalized field, not only the status and plan.
                row.mission = job.mission.model_dump(mode="json")
                row.plan = job.plan.model_dump(mode="json")
                row.status = job.status.value
                row.message = job.message
                row.attempts = job.attempts
                row.updated_at = job.updated_at
                recovered.append(job)
            session.commit()
        return recovered

    def list_all(self) -> list[MissionJob]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(MissionJobRow).order_by(MissionJobRow.created_at.desc())
            ).all()
            jobs: list[MissionJob] = []
            changed = False
            for row in rows:
                job = _safe_job(MissionJob(
                    id=row.id,
                    mission=CompanyMission.model_validate(row.mission),
                    plan=MissionPlan.model_validate(row.plan),
                    status=MissionJobStatus(row.status),
                    message=row.message,
                    workspace_id=row.workspace_id,
                    attempts=row.attempts,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                ))
                changed = _rewrite_safe_job_row(row, job) or changed
                jobs.append(job)
            if changed:
                session.commit()
            return jobs

    def delete_many(self, mission_ids: set[str]) -> int:
        if not mission_ids:
            return 0
        with Session(self._engine) as session:
            result = session.execute(
                delete(MissionJobRow).where(MissionJobRow.id.in_(mission_ids))
            )
            session.commit()
            return int(result.rowcount or 0)

    def close(self) -> None:
        self._engine.dispose()



class ProjectOutputStore:
    """Durable project output manifests."""

    def __init__(self) -> None:
        url = settings.database_url.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg://",
        )
        self._engine = create_engine(url, pool_pre_ping=True)

    def save(self, manifest: ProjectOutputManifest) -> None:
        manifest = _safe_output_manifest(manifest)
        with Session(self._engine) as session:
            row = session.get(ProjectOutputRow, manifest.id)
            values = {
                "mission_id": manifest.mission_id,
                "project_id": manifest.project_id,
                "name": manifest.name,
                "status": manifest.status,
                "output_type": manifest.output_type,
                "repository": manifest.repository,
                "github_message": manifest.github_message,
                "memory_id": manifest.memory_id,
                "created_at": manifest.created_at,
                "updated_at": manifest.updated_at,
            }
            if row is None:
                session.add(ProjectOutputRow(id=manifest.id, **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            session.commit()

    def get_for_mission(self, mission_id: str) -> list[ProjectOutputManifest]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(ProjectOutputRow)
                .where(ProjectOutputRow.mission_id == mission_id)
                .order_by(ProjectOutputRow.created_at.desc())
            ).all()
            return [self._model(row) for row in rows]

    def _model(self, row: ProjectOutputRow) -> ProjectOutputManifest:
        return _safe_output_manifest(ProjectOutputManifest(
            id=row.id,
            mission_id=row.mission_id,
            project_id=row.project_id,
            name=row.name,
            status=row.status,
            output_type=row.output_type,
            repository=row.repository,
            github_message=row.github_message,
            memory_id=row.memory_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        ))

    def close(self) -> None:
        self._engine.dispose()


class MissionAuditStore:
    """Durable append-only mission audit history."""

    def __init__(self) -> None:
        url = settings.database_url.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg://",
        )
        self._engine = create_engine(url, pool_pre_ping=True)

    def append(self, entry: MissionAuditEntry) -> None:
        entry = _safe_audit_entry(entry)
        with Session(self._engine) as session:
            session.add(
                MissionAuditRow(
                    id=entry.id,
                    mission_id=entry.mission_id,
                    event_type=entry.event_type,
                    message=entry.message,
                    status=entry.status,
                    timestamp=entry.timestamp,
                    metadata=entry.metadata,
                )
            )
            session.commit()

    def list_for_mission(
        self,
        mission_id: str,
        event_type: str | None = None,
        status: str | None = None,
        limit: int = 500,
    ) -> list[MissionAuditEntry]:
        """Return the newest bounded page of audit entries in chronological order."""
        with Session(self._engine) as session:
            query = select(MissionAuditRow).where(MissionAuditRow.mission_id == mission_id)
            if event_type:
                query = query.where(MissionAuditRow.event_type == event_type)
            if status:
                query = query.where(MissionAuditRow.status == status)
            rows = session.scalars(
                query.order_by(MissionAuditRow.timestamp.desc()).limit(_bounded_audit_limit(limit))
            ).all()
            rows.reverse()
            return [
                _safe_audit_entry(MissionAuditEntry(
                    id=row.id,
                    mission_id=row.mission_id,
                    event_type=row.event_type,
                    message=row.message,
                    status=row.status,
                    timestamp=row.timestamp,
                    metadata=row.metadata,
                ))
                for row in rows
            ]

    def close(self) -> None:
        self._engine.dispose()


class ProjectStore:
    """Durable store for project-factory state."""

    def __init__(self) -> None:
        url = settings.database_url.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg://",
        )
        self._engine = create_engine(url, pool_pre_ping=True)

    def save(self, project: FactoryProject) -> None:
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            row = session.get(FactoryProjectRow, project.mission.id)
            values = {
                **_safe_factory_snapshot(project),
                "updated_at": now,
            }
            if row is None:
                session.add(FactoryProjectRow(id=project.mission.id, **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            session.commit()

    def load_pending(self) -> list[dict]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(FactoryProjectRow)
                .where(FactoryProjectRow.status.in_(["queued", "running"]))
                .order_by(FactoryProjectRow.updated_at)
            ).all()
            pending: list[dict] = []
            changed = False
            for row in rows:
                # A single malformed legacy snapshot must not prevent every
                # other queued mission from being recovered after restart.
                try:
                    mission = _safe_mission(CompanyMission.model_validate(row.mission))
                    plan = _safe_plan(MissionPlan.model_validate(row.plan))
                    status = row.status
                    if status == "running":
                        plan = recover_running_plan(plan)
                        status = "queued"
                    stages_executed = max(0, int(row.stages_executed))
                    attempts = max(0, int(row.attempts))
                    safe_mission = mission.model_dump(mode="json")
                    safe_plan = plan.model_dump(mode="json")
                except (TypeError, ValueError, OverflowError):
                    # Keep diagnostics generic: validation errors can echo
                    # untrusted persisted values, including secret-like text.
                    logging.getLogger(__name__).error(
                        "Quarantining malformed pending factory snapshot"
                    )
                    # Remove the row from the pending query on future starts,
                    # while preserving it for operator inspection.
                    row.status = "blocked"
                    row.updated_at = datetime.now(UTC)
                    changed = True
                    continue
                if (
                    row.mission != safe_mission
                    or row.plan != safe_plan
                    or row.status != status
                    or row.stages_executed != stages_executed
                    or row.attempts != attempts
                ):
                    row.mission = safe_mission
                    row.plan = safe_plan
                    row.status = status
                    row.stages_executed = stages_executed
                    row.attempts = attempts
                    changed = True
                pending.append({
                    "mission": mission,
                    "plan": plan,
                    "status": status,
                    "stages_executed": stages_executed,
                    "attempts": attempts,
                    "last_error": None,
                })
            if changed:
                session.commit()
            return pending

    def delete_many(self, mission_ids: set[str]) -> int:
        if not mission_ids:
            return 0
        with Session(self._engine) as session:
            result = session.execute(
                delete(FactoryProjectRow).where(FactoryProjectRow.id.in_(mission_ids))
            )
            session.commit()
            return int(result.rowcount or 0)

    def close(self) -> None:
        self._engine.dispose()
