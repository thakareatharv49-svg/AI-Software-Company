"""Associate existing project records with their owning workspace."""
from alembic import op
import sqlalchemy as sa
revision = "m63_project_workspace"
down_revision = "m62_workspace_entitlements"
branch_labels = None
depends_on = None
COMPANY_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"

def upgrade() -> None:
    op.add_column("projects", sa.Column("workspace_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_projects_workspace_id_workspaces", "projects", "workspaces", ["workspace_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])
    op.execute(sa.text("UPDATE projects SET workspace_id = :workspace_id WHERE workspace_id IS NULL").bindparams(workspace_id=COMPANY_WORKSPACE_ID))

def downgrade() -> None:
    op.drop_index("ix_projects_workspace_id", table_name="projects")
    op.drop_constraint("fk_projects_workspace_id_workspaces", "projects", type_="foreignkey")
    op.drop_column("projects", "workspace_id")
