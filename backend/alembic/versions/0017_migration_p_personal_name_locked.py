"""migration P: personal_name_locked

Revision ID: 0017_migration_p
Revises: 0016_migration_o
Create Date: 2026-06-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_migration_p"
down_revision: Union[str, None] = "0016_migration_o"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("personal_name_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("users", "personal_name_locked", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "personal_name_locked")
