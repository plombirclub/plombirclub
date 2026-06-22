"""migration H: prize distributors visibility

Revision ID: 0009_migration_h
Revises: 0008_migration_g
Create Date: 2026-06-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009_migration_h"
down_revision: Union[str, None] = "0008_migration_g"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prize_distributors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prize_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["prize_id"],
            ["prizes.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["distributor_id"],
            ["distributors.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prize_id",
            "distributor_id",
            name="uq_prize_distributors_prize_distributor",
        ),
    )
    op.create_index(
        "ix_prize_distributors_prize_id",
        "prize_distributors",
        ["prize_id"],
    )
    op.create_index(
        "ix_prize_distributors_distributor_id",
        "prize_distributors",
        ["distributor_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_prize_distributors_distributor_id", table_name="prize_distributors")
    op.drop_index("ix_prize_distributors_prize_id", table_name="prize_distributors")
    op.drop_table("prize_distributors")
