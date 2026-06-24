"""migration N: agreements_accepted_at

Revision ID: 0015_migration_n
Revises: 0014_migration_m
Create Date: 2026-06-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_migration_n"
down_revision = "0014_migration_m"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("agreements_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "agreements_accepted_at")
