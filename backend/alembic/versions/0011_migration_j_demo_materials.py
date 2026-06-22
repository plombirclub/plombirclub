"""migration J: demo materials for ЛК preview

Revision ID: 0011_migration_j
Revises: 0010_migration_i
Create Date: 2026-06-21
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "0011_migration_j"
down_revision: Union[str, None] = "0010_migration_i"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_MATERIALS = (
    (
        uuid.UUID("e1000001-0000-4000-8000-000000000001"),
        "Фабрика мороженого",
        "Краткий обзор производства «Чистая Линия». Материал для ознакомления участников акции.",
        0,
    ),
    (
        uuid.UUID("e1000002-0000-4000-8000-000000000001"),
        "Рабочий день торгового представителя",
        "Информационный материал о типовом рабочем дне ТП. Содержимое будет дополнено администратором.",
        1,
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    for material_id, title, description, sort_order in DEMO_MATERIALS:
        bind.execute(
            sa.text(
                """
                INSERT INTO materials (
                    id, title, description, content_type, file_path,
                    total_pages, is_published, sort_order, created_at, updated_at
                )
                VALUES (
                    :id, :title, :description, 'text', NULL,
                    NULL, true, :sort_order, now(), now()
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": str(material_id),
                "title": title,
                "description": description,
                "sort_order": sort_order,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    for material_id, _, _, _ in DEMO_MATERIALS:
        bind.execute(
            sa.text("DELETE FROM materials WHERE id = :id"),
            {"id": str(material_id)},
        )
