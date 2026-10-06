from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.company.audit import MissionAuditEntry
from src.company.mission_controller.models import MissionPlan
from src.company.project_outputs import ProjectOutputManifest
from src.company.mission_jobs import MissionJob, MissionJobStatus, recover_running_job
from src.company.models.contracts import CompanyMission
from src.config.settings import settings
from src.db.base import Base

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
        with Session(self._engine) as session:
            row = session.get(MissionJobRow, job.id)
            values = {
                "mission": job.mission.model_dump(mode="json"),
                "plan": job.plan.model_dump(mode="json"),
                "status": getattr(job.status, "value", job.status),
                "message": job.message,
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
            return MissionJob(
                id=row.id,
                mission=CompanyMission.model_validate(row.mission),
                plan=MissionPlan.model_validate(row.plan),
                status=MissionJobStatus(row.status),
                message=row.message,
                attempts=row.attempts,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    def recover_running(self) -> list[MissionJob]:
        recovered: list[MissionJob] = []
        with Session(self._engine) as session:
            rows = session.scalars(
                select(MissionJobRow).where(MissionJobRow.status == MissionJobStatus.RUNNING.value)
            ).all()
            for row in rows:
                job = MissionJob(
                    id=row.id,
                    mission=CompanyMission.model_validate(row.mission),
                    plan=MissionPlan.model_validate(row.plan),
                    status=MissionJobStatus(row.status),
                    message=row.message,
                    attempts=row.attempts,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                job = recover_running_job(job)
                row.status = job.status.value
                row.message = job.message
                row.updated_at = job.updated_at
                recovered.append(job)
            session.commit()
        return recovered

    def list_all(self) -> list[MissionJob]:
        with Session(self._engine) as session:
            rows = session.scalars(
                select(MissionJobRow).order_by(MissionJobRow.created_at.desc())
            ).all()
            return [
                MissionJob(
                    id=row.id,
                    mission=CompanyMission.model_validate(row.mission),
                    plan=MissionPlan.model_validate(row.plan),
                    status=MissionJobStatus(row.status),
                    message=row.message,
                    attempts=row.attempts,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]

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
        return ProjectOutputManifest(
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
        )

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
    ) -> list[MissionAuditEntry]:
        with Session(self._engine) as session:
            query = select(MissionAuditRow).where(MissionAuditRow.mission_id == mission_id)
            if event_type:
                query = query.where(MissionAuditRow.event_type == event_type)
            if status:
                query = query.where(MissionAuditRow.status == status)
            rows = session.scalars(query.order_by(MissionAuditRow.timestamp.asc())).all()
            return [
                MissionAuditEntry(
                    id=row.id,
                    mission_id=row.mission_id,
                    event_type=row.event_type,
                    message=row.message,
                    status=row.status,
                    timestamp=row.timestamp,
                    metadata=row.metadata,
                )
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
                "mission": project.mission.model_dump(mode="json"),
                "plan": project.plan.model_dump(mode="json"),
                "status": project.status,
                "stages_executed": project.stages_executed,
                "attempts": project.attempts,
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
            return [
                {
                    "mission": CompanyMission.model_validate(row.mission),
                    "plan": MissionPlan.model_validate(row.plan),
                    "status": "queued" if row.status == "running" else row.status,
                    "stages_executed": row.stages_executed,
                    "attempts": row.attempts,
                    "last_error": None,
                }
                for row in rows
            ]

    def close(self) -> None:
        self._engine.dispose()
