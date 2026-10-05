from alembic import op
import sqlalchemy as sa

revision = "m55_mission_audit"
down_revision = "m53_mission_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mission_audit",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=5000), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mission_audit_mission_id", "mission_audit", ["mission_id"])


def downgrade() -> None:
    op.drop_index("ix_mission_audit_mission_id", table_name="mission_audit")
    op.drop_table("mission_audit")
