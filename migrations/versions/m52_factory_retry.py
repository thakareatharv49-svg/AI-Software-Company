"""add factory retry state

Revision ID: m52_factory_retry
Revises: m51_factory_state
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m52_factory_retry"
down_revision: str | Sequence[str] | None = "m51_factory_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("factory_projects", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("factory_projects", "attempts")
