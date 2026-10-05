from alembic import op
import sqlalchemy as sa

revision = "m57_project_outputs"
down_revision = "m55_mission_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_outputs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("output_type", sa.String(length=64), nullable=False),
        sa.Column("repository", sa.String(length=500), nullable=True),
        sa.Column("github_message", sa.String(length=5000), nullable=True),
        sa.Column("memory_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_outputs_mission_id", "project_outputs", ["mission_id"])
    op.create_index("ix_project_outputs_project_id", "project_outputs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_outputs_project_id", table_name="project_outputs")
    op.drop_index("ix_project_outputs_mission_id", table_name="project_outputs")
    op.drop_table("project_outputs")
