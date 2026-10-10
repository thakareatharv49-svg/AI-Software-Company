"""Link workspace projects to the factory mission that builds them."""
from alembic import op
import sqlalchemy as sa

revision = "m65_project_factory_launch"
down_revision = "m64_mission_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("mission_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_projects_mission_id_mission_jobs",
        "projects",
        "mission_jobs",
        ["mission_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_projects_mission_id", "projects", ["mission_id"])


def downgrade() -> None:
    op.drop_index("ix_projects_mission_id", table_name="projects")
    op.drop_constraint(
        "fk_projects_mission_id_mission_jobs",
        "projects",
        type_="foreignkey",
    )
    op.drop_column("projects", "mission_id")
