"""Associate durable factory jobs with their owning workspace.

Existing missions are company-owned, so they are backfilled to the company workspace.
"""
from alembic import op
import sqlalchemy as sa

revision = "m64_mission_workspace"
down_revision = "m63_project_workspace"
branch_labels = None
depends_on = None

COMPANY_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.add_column(
        "mission_jobs",
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_mission_jobs_workspace_id_workspaces",
        "mission_jobs",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_mission_jobs_workspace_id", "mission_jobs", ["workspace_id"])
    op.execute(
        sa.text(
            "UPDATE mission_jobs SET workspace_id = :workspace_id "
            "WHERE workspace_id IS NULL"
        ).bindparams(workspace_id=COMPANY_WORKSPACE_ID)
    )


def downgrade() -> None:
    op.drop_index("ix_mission_jobs_workspace_id", table_name="mission_jobs")
    op.drop_constraint(
        "fk_mission_jobs_workspace_id_workspaces",
        "mission_jobs",
        type_="foreignkey",
    )
    op.drop_column("mission_jobs", "workspace_id")
