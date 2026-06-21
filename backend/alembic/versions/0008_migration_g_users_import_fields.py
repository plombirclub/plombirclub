"""migration G: users import fields

Revision ID: 0008_migration_g
Revises: 0007_migration_f
Create Date: 2026-06-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_migration_g"
down_revision: Union[str, None] = "0007_migration_f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("participant_code", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("participant_position", sa.String(length=50), nullable=True))
    op.create_index("ix_users_participant_code", "users", ["participant_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_participant_code", table_name="users")
    op.drop_column("users", "participant_position")
    op.drop_column("users", "participant_code")
