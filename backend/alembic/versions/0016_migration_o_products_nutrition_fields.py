"""migration O: add product nutrition fields

Revision ID: 0016_migration_o
Revises: 0015_migration_n
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_migration_o"
down_revision = "0015_migration_n"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("shelf_life", sa.String(length=100), nullable=True))
    op.add_column("products", sa.Column("nutrition_facts", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "nutrition_facts")
    op.drop_column("products", "shelf_life")
