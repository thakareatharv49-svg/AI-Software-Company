"""Add server-side workspace plan entitlements and monthly usage."""
from alembic import op
import sqlalchemy as sa
revision = "m62_workspace_entitlements"
down_revision = "m61_identity_workspaces"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("workspace_entitlements", sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True), sa.Column("plan", sa.String(16), nullable=False, server_default="free"), sa.Column("status", sa.String(16), nullable=False, server_default="active"), sa.Column("monthly_run_limit", sa.Integer(), nullable=False, server_default="10"), sa.Column("project_limit", sa.Integer(), nullable=False, server_default="3"), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("plan IN ('demo', 'free', 'pro', 'team')", name="ck_workspace_entitlements_plan"), sa.CheckConstraint("status IN ('active', 'past_due', 'cancelled', 'expired')", name="ck_workspace_entitlements_status"))
    op.create_table("workspace_usage", sa.Column("id", sa.String(36), primary_key=True), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("period_start", sa.DateTime(timezone=True), nullable=False), sa.Column("runs_used", sa.Integer(), nullable=False, server_default="0"), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("workspace_id", "period_start", name="uq_workspace_usage_period"), sa.CheckConstraint("runs_used >= 0", name="ck_workspace_usage_runs_nonnegative"))
    op.create_index("ix_workspace_usage_workspace_id", "workspace_usage", ["workspace_id"])

def downgrade() -> None:
    op.drop_index("ix_workspace_usage_workspace_id", table_name="workspace_usage")
    op.drop_table("workspace_usage")
    op.drop_table("workspace_entitlements")
