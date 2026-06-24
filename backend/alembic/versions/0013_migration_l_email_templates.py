"""migration L: email_templates for SMTP letter texts

Revision ID: 0013_migration_l
Revises: 0012_migration_k
Create Date: 2026-06-23
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "0013_migration_l"
down_revision: Union[str, None] = "0012_migration_k"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMAIL_TEMPLATES = (
    (
        uuid.UUID("d0000001-0000-4000-8000-000000000001"),
        "email_import_welcome",
        "PlombirClub — доступ к порталу",
        (
            "Здравствуйте, уважаемый участник!\n"
            "Направляем ваш доступ к мотивационному порталу «PlombirClub».\n"
            "Данные вашей учетной записи:\n"
            "Логин: {login}\n"
            "Временный пароль: {temporary_password}\n"
            "Для завершения регистрации пройдите по ссылке, придумайте и измените пароль: {site_url}"
        ),
    ),
    (
        uuid.UUID("d0000002-0000-4000-8000-000000000001"),
        "email_verification_code",
        "PlombirClub — код подтверждения телефона",
        (
            "Здравствуйте, уважаемый участник! Вы зарегистрировали номер телефона ({phone}) "
            "в личном кабинете промо-портала «PlombirClub». Пожалуйста, проверьте номер телефона "
            "и введите код подтверждения {code} на сайте «PlombirClub». Срок действия кода 5 минут"
        ),
    ),
    (
        uuid.UUID("d0000003-0000-4000-8000-000000000001"),
        "email_forgot_password",
        "PlombirClub — восстановление пароля",
        (
            "Здравствуйте, уважаемый участник! Ваш новый временный пароль на сайте "
            "«PlombirClub» {temporary_password}. Пожалуйста, придумайте и измените временный "
            "пароль на сайте {site_url}"
        ),
    ),
    (
        uuid.UUID("d0000004-0000-4000-8000-000000000001"),
        "email_sbp_verification",
        "PlombirClub — подтверждение заявки СБП",
        (
            "Здравствуйте, уважаемый участник! Вы создали заявку с номером телефона ({phone}) "
            "в личном кабинете промо-портала «PlombirClub». Пожалуйста, проверьте номер телефона "
            "и введите код подтверждения {code} на сайте «PlombirClub». Срок действия кода 5 минут"
        ),
    ),
)


def upgrade() -> None:
    op.create_table(
        "email_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_type"),
    )

    bind = op.get_bind()
    for template_id, event_type, subject, template_text in EMAIL_TEMPLATES:
        bind.execute(
            sa.text(
                """
                INSERT INTO email_templates (id, event_type, subject, template_text, updated_at)
                VALUES (:id, :event_type, :subject, :template_text, now())
                ON CONFLICT (event_type) DO NOTHING
                """
            ),
            {
                "id": str(template_id),
                "event_type": event_type,
                "subject": subject,
                "template_text": template_text,
            },
        )


def downgrade() -> None:
    op.drop_table("email_templates")
