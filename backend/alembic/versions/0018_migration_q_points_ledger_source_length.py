"""migration Q: widen points_ledger.source for import_sales keys

Revision ID: 0018_migration_q
Revises: 0017_migration_p
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018_migration_q"
down_revision: Union[str, None] = "0017_migration_p"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "points_ledger",
        "source",
        existing_type=sa.String(length=50),
        type_=sa.String(length=128),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "points_ledger",
        "source",
        existing_type=sa.String(length=128),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
