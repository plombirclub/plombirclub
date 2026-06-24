import logging
import smtplib
from email.message import EmailMessage
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.email_template import EmailTemplate
from app.models.user import User
from app.services.users import write_admin_log

logger = logging.getLogger(__name__)

EMAIL_EVENT_LABELS: dict[str, str] = {
    "email_import_welcome": "Импорт участника",
    "email_verification_code": "Код при первом входе",
    "email_forgot_password": "Восстановление пароля",
    "email_sbp_verification": "Код для заявки СБП",
}

EMAIL_PLACEHOLDER_HINTS: dict[str, str] = {
    "email_import_welcome": "{login}, {temporary_password}, {site_url}",
    "email_verification_code": "{phone}, {code}, {site_url}",
    "email_forgot_password": "{temporary_password}, {site_url}",
    "email_sbp_verification": "{phone}, {code}, {site_url}",
}


def format_phone_display(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("7"):
        return "8" + digits[1:]
    return digits or phone


def login_site_url() -> str:
    return f"{settings.app_url.rstrip('/')}/pages/login.html"


def _serialize_template(template: EmailTemplate) -> dict[str, Any]:
    return {
        "id": str(template.id),
        "event_type": template.event_type,
        "event_label": EMAIL_EVENT_LABELS.get(template.event_type, template.event_type),
        "subject": template.subject,
        "template_text": template.template_text,
        "placeholders": EMAIL_PLACEHOLDER_HINTS.get(template.event_type, ""),
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


class EmailService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_template(self, event_type: str) -> EmailTemplate | None:
        return await self.db.scalar(
            select(EmailTemplate).where(EmailTemplate.event_type == event_type)
        )

    async def render(
        self,
        event_type: str,
        **template_vars: Any,
    ) -> tuple[str, str] | None:
        template = await self.get_template(event_type)
        if template is None:
            return None

        normalized_vars = {key: str(value) for key, value in template_vars.items()}
        try:
            body = template.template_text.format(**normalized_vars)
        except KeyError:
            body = template.template_text
        try:
            subject = template.subject.format(**normalized_vars)
        except KeyError:
            subject = template.subject
        return subject, body

    @staticmethod
    def _send_smtp(*, to_email: str, subject: str, body: str) -> str | None:
        if not settings.smtp_user or not settings.smtp_password:
            return "SMTP не настроен: письмо не отправлено"

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from_email or settings.smtp_user
        message["To"] = to_email
        message.set_content(body)

        try:
            if settings.smtp_use_tls:
                with smtplib.SMTP_SSL(
                    host=settings.smtp_host,
                    port=settings.smtp_port,
                    timeout=20,
                ) as smtp:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(
                    host=settings.smtp_host,
                    port=settings.smtp_port,
                    timeout=20,
                ) as smtp:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                    smtp.send_message(message)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Не удалось отправить email на %s", to_email)
            return str(exc)
        return None

    async def send(
        self,
        *,
        event_type: str,
        to_email: str,
        **template_vars: Any,
    ) -> str | None:
        rendered = await self.render(event_type, **template_vars)
        if rendered is None:
            return f"Шаблон email не найден: {event_type}"
        subject, body = rendered
        return self._send_smtp(to_email=to_email, subject=subject, body=body)

    async def send_import_welcome(
        self,
        *,
        to_email: str,
        temporary_password: str,
    ) -> str | None:
        return await self.send(
            event_type="email_import_welcome",
            to_email=to_email,
            login=to_email,
            temporary_password=temporary_password,
            site_url=login_site_url(),
        )

    async def send_verification_code(
        self,
        *,
        to_email: str,
        phone: str,
        code: str,
    ) -> str | None:
        return await self.send(
            event_type="email_verification_code",
            to_email=to_email,
            phone=format_phone_display(phone),
            code=code,
            site_url=login_site_url(),
        )

    async def send_forgot_password(
        self,
        *,
        to_email: str,
        temporary_password: str,
    ) -> str | None:
        return await self.send(
            event_type="email_forgot_password",
            to_email=to_email,
            temporary_password=temporary_password,
            site_url=login_site_url(),
        )

    async def send_sbp_verification_code(
        self,
        *,
        to_email: str,
        payout_phone: str,
        code: str,
    ) -> str | None:
        return await self.send(
            event_type="email_sbp_verification",
            to_email=to_email,
            phone=format_phone_display(payout_phone),
            code=code,
            site_url=login_site_url(),
        )

    async def list_templates(self) -> list[dict[str, Any]]:
        templates = (
            await self.db.scalars(
                select(EmailTemplate).order_by(EmailTemplate.event_type.asc())
            )
        ).all()
        return [_serialize_template(template) for template in templates]

    async def update_template(
        self,
        *,
        admin: User,
        template_id: uuid.UUID,
        subject: str,
        template_text: str,
    ) -> dict[str, Any]:
        normalized_subject = subject.strip()
        normalized_text = template_text.strip()
        if not normalized_subject:
            raise ValueError("Тема письма не может быть пустой")
        if not normalized_text:
            raise ValueError("Текст письма не может быть пустым")

        template = await self.db.scalar(
            select(EmailTemplate).where(EmailTemplate.id == template_id)
        )
        if template is None:
            raise LookupError("Шаблон email не найден")

        old_value = _serialize_template(template)
        template.subject = normalized_subject
        template.template_text = normalized_text

        await write_admin_log(
            self.db,
            admin=admin,
            action="update_email_template",
            entity_type="email_template",
            entity_id=template.id,
            old_value=old_value,
            new_value={
                "subject": normalized_subject,
                "template_text": normalized_text,
            },
        )
        await self.db.commit()
        await self.db.refresh(template)
        return _serialize_template(template)
