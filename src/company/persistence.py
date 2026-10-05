from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.company.mission_controller.models import MissionPlan
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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
                }
                for row in rows
            ]

    def close(self) -> None:
        self._engine.dispose()
