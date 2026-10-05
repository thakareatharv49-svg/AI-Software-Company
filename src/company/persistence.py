from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.company.mission_controller.models import MissionPlan
from src.company.audit import MissionAuditEntry
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
                "status": job.status.value,
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
