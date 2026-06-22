"""migration K: points_activation notification template

Revision ID: 0012_migration_k
Revises: 0011_migration_j
Create Date: 2026-06-21
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "0012_migration_k"
down_revision: Union[str, None] = "0011_migration_j"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POINTS_ACTIVATION_TEMPLATE_ID = uuid.UUID("c0000009-0000-4000-8000-000000000001")


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO notification_templates (id, event_type, template_text, updated_at)
            VALUES (:id, :event_type, :template_text, now())
            ON CONFLICT (event_type) DO NOTHING
            """
        ),
        {
            "id": str(POINTS_ACTIVATION_TEMPLATE_ID),
            "event_type": "points_activation",
            "template_text": (
                "Доступна активация баллов за период {period_month}. "
                "Перейдите в личный кабинет и активируйте начисления."
            ),
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM notification_templates WHERE id = :id"),
        {"id": str(POINTS_ACTIVATION_TEMPLATE_ID)},
    )
