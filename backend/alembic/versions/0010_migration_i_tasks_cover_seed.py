"""migration I: tasks cover_image_path, test user distributor, demo tasks

Revision ID: 0010_migration_i
Revises: 0009_migration_h
Create Date: 2026-06-21
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "0010_migration_i"
down_revision: Union[str, None] = "0009_migration_h"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_DISTRIBUTOR_MOSCOW = "b0000002-0000-4000-8000-000000000001"
TEST_USER_EMAIL = "testuser@plombirclub.ru"

DEMO_TASKS = (
    (
        uuid.UUID("d1000001-0000-4000-8000-000000000001"),
        "Мотивационная программа на июнь 2026",
        (
            "<p>Уважаемые участники!</p>"
            "<p><strong>Торговые представители:</strong></p>"
            "<ul><li>Условие №1 — продайте целевой объём продукции.</li>"
            "<li>Условие №2 — выполните задания в разделе «Задания».</li></ul>"
            "<p><strong>Начисление баллов:</strong> баллы начисляются после импорта продаж из Excel.</p>"
        ),
        "2026-06",
    ),
    (
        uuid.UUID("d1000002-0000-4000-8000-000000000001"),
        "Мотивационная программа на май 2026",
        (
            "<p>Уважаемые участники!</p>"
            "<p>Мотивационная программа на май 2026: выполните план продаж и активируйте баллы "
            "в срок до 15 числа следующего месяца.</p>"
        ),
        "2026-05",
    ),
    (
        uuid.UUID("d1000003-0000-4000-8000-000000000001"),
        "Старт мотивационной программы 2026",
        (
            "<p>Добро пожаловать в программу мотивации «Чистая Линия»!</p>"
            "<p>Ознакомьтесь с правилами, примите участие и следите за уведомлениями в личном кабинете.</p>"
        ),
        "2026-03",
    ),
)


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("cover_image_path", sa.String(length=500), nullable=True),
    )

    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            UPDATE users
            SET distributor_id = :distributor_id, updated_at = now()
            WHERE email = :email AND distributor_id IS NULL
            """
        ),
        {"distributor_id": SEED_DISTRIBUTOR_MOSCOW, "email": TEST_USER_EMAIL},
    )

    for task_id, title, content, period_month in DEMO_TASKS:
        bind.execute(
            sa.text(
                """
                INSERT INTO tasks (
                    id, title, content, period_month, task_type, source,
                    is_published, created_by, created_at, published_at, cover_image_path
                )
                SELECT
                    :id, :title, :content, :period_month, 'participation_conditions', 'admin',
                    true, NULL, now(), now(), NULL
                WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = :id)
                """
            ),
            {
                "id": str(task_id),
                "title": title,
                "content": content,
                "period_month": period_month,
            },
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO task_distributors (task_id, distributor_id)
                SELECT :task_id, :distributor_id
                WHERE NOT EXISTS (
                    SELECT 1 FROM task_distributors
                    WHERE task_id = :task_id AND distributor_id = :distributor_id
                )
                """
            ),
            {
                "task_id": str(task_id),
                "distributor_id": SEED_DISTRIBUTOR_MOSCOW,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    for task_id, _, _, _ in DEMO_TASKS:
        bind.execute(
            sa.text("DELETE FROM task_distributors WHERE task_id = :task_id"),
            {"task_id": str(task_id)},
        )
        bind.execute(
            sa.text("DELETE FROM tasks WHERE id = :task_id"),
            {"task_id": str(task_id)},
        )
    op.drop_column("tasks", "cover_image_path")
