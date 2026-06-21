"""migration F: FK request_id, indexes, seed data

Revision ID: 0007_migration_f
Revises: 0006_migration_e
Create Date: 2026-06-20

"""
from typing import Sequence, Union
import json
import uuid

import bcrypt
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0007_migration_f"
down_revision: Union[str, None] = "0006_migration_e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Фиксированные UUID seed-данных — стабильны между окружениями.
SEED_ADMIN_ID = uuid.UUID("b0000001-0000-4000-8000-000000000001")
SEED_DISTRIBUTOR_1_ID = uuid.UUID("b0000002-0000-4000-8000-000000000001")
SEED_DISTRIBUTOR_2_ID = uuid.UUID("b0000003-0000-4000-8000-000000000001")
SEED_SUPPORT_SETTING_ID = uuid.UUID("b0000004-0000-4000-8000-000000000001")

NOTIFICATION_TEMPLATES = (
    (
        uuid.UUID("c0000001-0000-4000-8000-000000000001"),
        "task_published",
        "Опубликованы условия программы мотивации на {period_month}. "
        "Пожалуйста, ознакомьтесь с ними в Личном кабинете.",
    ),
    (
        uuid.UUID("c0000002-0000-4000-8000-000000000001"),
        "request_created",
        "Ваша заявка на приз создана и принята в обработку.",
    ),
    (
        uuid.UUID("c0000003-0000-4000-8000-000000000001"),
        "request_phone_verification_required",
        "Для завершения заявки по СБП необходимо подтвердить номер телефона.",
    ),
    (
        uuid.UUID("c0000004-0000-4000-8000-000000000001"),
        "request_confirmed",
        "Ваша заявка подтверждена администратором.",
    ),
    (
        uuid.UUID("c0000005-0000-4000-8000-000000000001"),
        "request_rejected",
        "Ваша заявка отклонена. Причина: {reason}. Баллы возвращены на ваш счёт.",
    ),
    (
        uuid.UUID("c0000006-0000-4000-8000-000000000001"),
        "request_fulfilled",
        "Ваша заявка выполнена. Проверьте детали в разделе «Мои заявки».",
    ),
    (
        uuid.UUID("c0000007-0000-4000-8000-000000000001"),
        "inn_verified",
        "Администратор подтвердил ваш ИНН. Теперь вы можете создавать заявки на призы.",
    ),
    (
        uuid.UUID("c0000008-0000-4000-8000-000000000001"),
        "self_employed_verified",
        "Администратор подтвердил ваш статус самозанятого.",
    ),
)

SEED_ADMIN_EMAIL = "admin@plombirclub.ru"
SEED_ADMIN_PASSWORD = "Admin123!"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def upgrade() -> None:
    op.create_foreign_key(
        "fk_points_ledger_request_id_requests",
        "points_ledger",
        "requests",
        ["request_id"],
        ["id"],
        ondelete="SET NULL",
        onupdate="CASCADE",
    )
    op.create_foreign_key(
        "fk_points_operations_log_request_id_requests",
        "points_operations_log",
        "requests",
        ["request_id"],
        ["id"],
        ondelete="SET NULL",
        onupdate="CASCADE",
    )
    op.create_index(
        "ix_points_ledger_request_id",
        "points_ledger",
        ["request_id"],
    )
    op.create_index(
        "ix_points_operations_log_request_id",
        "points_operations_log",
        ["request_id"],
    )
    op.create_unique_constraint("uq_distributors_name", "distributors", ["name"])

    bind = op.get_bind()
    password_hash = _hash_password(SEED_ADMIN_PASSWORD)

    bind.execute(
        sa.text(
            """
            INSERT INTO distributors (id, name, is_active, created_at)
            VALUES
                (:dist1_id, :dist1_name, true, now()),
                (:dist2_id, :dist2_name, true, now())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "dist1_id": str(SEED_DISTRIBUTOR_1_ID),
            "dist1_name": "Дистрибьютор Москва",
            "dist2_id": str(SEED_DISTRIBUTOR_2_ID),
            "dist2_name": "Дистрибьютор Санкт-Петербург",
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO users (
                id, email, password_hash, role, full_name,
                phone_verified, agreements_accepted,
                temporary_password_changed, is_registration_complete,
                is_active, created_at, updated_at
            ) VALUES (
                :admin_id, :email, :password_hash, 'admin', 'Администратор',
                true, true, true, true, true, now(), now()
            )
            ON CONFLICT (email) DO NOTHING
            """
        ),
        {
            "admin_id": str(SEED_ADMIN_ID),
            "email": SEED_ADMIN_EMAIL,
            "password_hash": password_hash,
        },
    )

    support_value = json.dumps(
        {
            "phone": "",
            "email": "",
            "work_hours": "",
            "text": "",
        },
        ensure_ascii=False,
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO admin_settings (
                id, admin_id, setting_key, setting_value, created_at, updated_at
            ) VALUES (
                :id, :admin_id, 'support_contacts', CAST(:setting_value AS jsonb),
                now(), now()
            )
            ON CONFLICT ON CONSTRAINT uq_admin_settings_admin_id_setting_key DO NOTHING
            """
        ),
        {
            "id": str(SEED_SUPPORT_SETTING_ID),
            "admin_id": str(SEED_ADMIN_ID),
            "setting_value": support_value,
        },
    )

    for template_id, event_type, template_text in NOTIFICATION_TEMPLATES:
        bind.execute(
            sa.text(
                """
                INSERT INTO notification_templates (id, event_type, template_text, updated_at)
                VALUES (:id, :event_type, :template_text, now())
                ON CONFLICT (event_type) DO NOTHING
                """
            ),
            {
                "id": str(template_id),
                "event_type": event_type,
                "template_text": template_text,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()

    for template_id, _, _ in reversed(NOTIFICATION_TEMPLATES):
        bind.execute(
            sa.text("DELETE FROM notification_templates WHERE id = :id"),
            {"id": str(template_id)},
        )

    bind.execute(
        sa.text("DELETE FROM admin_settings WHERE id = :id"),
        {"id": str(SEED_SUPPORT_SETTING_ID)},
    )
    bind.execute(
        sa.text("DELETE FROM users WHERE id = :id"),
        {"id": str(SEED_ADMIN_ID)},
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM distributors
            WHERE id IN (:dist1_id, :dist2_id)
            """
        ),
        {
            "dist1_id": str(SEED_DISTRIBUTOR_1_ID),
            "dist2_id": str(SEED_DISTRIBUTOR_2_ID),
        },
    )

    op.drop_constraint("uq_distributors_name", "distributors", type_="unique")
    op.drop_index("ix_points_operations_log_request_id", table_name="points_operations_log")
    op.drop_index("ix_points_ledger_request_id", table_name="points_ledger")
    op.drop_constraint(
        "fk_points_operations_log_request_id_requests",
        "points_operations_log",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_points_ledger_request_id_requests",
        "points_ledger",
        type_="foreignkey",
    )
