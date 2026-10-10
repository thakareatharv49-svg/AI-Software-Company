"""Persistent server-side plan entitlements and usage counters."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class WorkspaceEntitlementModel(Base):
    __tablename__ = "workspace_entitlements"
    __table_args__ = (CheckConstraint("plan IN ('demo', 'free', 'pro', 'team')", name="ck_workspace_entitlements_plan"), CheckConstraint("status IN ('active', 'past_due', 'cancelled', 'expired')", name="ck_workspace_entitlements_status"))
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    plan: Mapped[str] = mapped_column(String(16), nullable=False, default="free")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    monthly_run_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    project_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class WorkspaceUsageModel(Base):
    __tablename__ = "workspace_usage"
    __table_args__ = (UniqueConstraint("workspace_id", "period_start", name="uq_workspace_usage_period"), CheckConstraint("runs_used >= 0", name="ck_workspace_usage_runs_nonnegative"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    runs_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
