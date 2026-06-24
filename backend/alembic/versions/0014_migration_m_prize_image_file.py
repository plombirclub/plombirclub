"""migration M: prize image_file_path

Revision ID: 0014_migration_m
Revises: 0013_migration_l
Create Date: 2026-06-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_migration_m"
down_revision = "0013_migration_l"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prizes",
        sa.Column("image_file_path", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prizes", "image_file_path")
