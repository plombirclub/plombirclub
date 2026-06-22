import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import Notification
from app.models.notification_template import NotificationTemplate
from app.models.user import User
from app.services.users import write_admin_log

EVENT_TITLES: dict[str, str] = {
    "points_activation": "Активация баллов",
    "task_published": "Условия акции",
    "request_created": "Заявка создана",
    "request_phone_verification_required": "Подтверждение телефона",
    "request_confirmed": "Заявка подтверждена",
    "request_rejected": "Заявка отклонена",
    "request_fulfilled": "Заявка выполнена",
    "inn_verified": "ИНН подтверждён",
    "self_employed_verified": "Статус самозанятого подтверждён",
}


def _serialize_notification(item: Notification) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "title": item.title,
        "message": item.message,
        "is_read": item.is_read,
        "template_id": str(item.template_id) if item.template_id else None,
        "event_type": item.template.event_type if item.template else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _serialize_template(template: NotificationTemplate) -> dict[str, Any]:
    return {
        "id": str(template.id),
        "event_type": template.event_type,
        "template_text": template.template_text,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def send(
        self,
        *,
        user_id: uuid.UUID,
        event_type: str,
        title: str | None = None,
        commit: bool = True,
        **template_vars: Any,
    ) -> Notification | None:
        template = await self.db.scalar(
            select(NotificationTemplate).where(NotificationTemplate.event_type == event_type)
        )
        if template is None:
            return None

        try:
            message = template.template_text.format(**template_vars)
        except KeyError:
            message = template.template_text

        notification = Notification(
            user_id=user_id,
            template_id=template.id,
            title=title or EVENT_TITLES.get(event_type, "Уведомление"),
            message=message,
        )
        self.db.add(notification)
        if commit:
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def send_batch(
        self,
        *,
        items: list[dict[str, Any]],
        commit: bool = True,
    ) -> dict[str, int]:
        sent_count = 0
        skipped_count = 0
        for item in items:
            user_id = item.get("user_id")
            event_type = item.get("event_type")
            if user_id is None or not event_type:
                skipped_count += 1
                continue
            template_vars = {
                key: value
                for key, value in item.items()
                if key not in {"user_id", "event_type", "title"}
            }
            notification = await self.send(
                user_id=user_id,
                event_type=event_type,
                title=item.get("title"),
                commit=False,
                **template_vars,
            )
            if notification is None:
                skipped_count += 1
            else:
                sent_count += 1

        if commit:
            await self.db.commit()
        return {"sent_count": sent_count, "skipped_count": skipped_count}

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        page: int,
        limit: int,
        unread_only: bool = False,
    ) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)

        conditions = [Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))

        total_count = await self.db.scalar(
            select(func.count(Notification.id)).where(*conditions)
        )
        total_count = int(total_count or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        items = (
            await self.db.scalars(
                select(Notification)
                .options(selectinload(Notification.template))
                .where(*conditions)
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        unread_count = await self.unread_count(user_id=user_id)

        return {
            "items": [_serialize_notification(item) for item in items],
            "unread_count": unread_count,
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def unread_count(self, *, user_id: uuid.UUID) -> int:
        count = await self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return int(count or 0)

    async def mark_read(
        self,
        *,
        user_id: uuid.UUID,
        notification_ids: list[uuid.UUID] | None = None,
        mark_all: bool = False,
    ) -> dict[str, Any]:
        if not mark_all and not notification_ids:
            raise ValueError("Укажите notification_ids или mark_all=true")

        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        if not mark_all and notification_ids:
            query = query.where(Notification.id.in_(notification_ids))

        items = (await self.db.scalars(query)).all()
        for item in items:
            item.is_read = True

        await self.db.commit()
        unread_count = await self.unread_count(user_id=user_id)
        return {"marked_count": len(items), "unread_count": unread_count}

    async def list_templates(self) -> list[dict[str, Any]]:
        templates = (
            await self.db.scalars(
                select(NotificationTemplate).order_by(NotificationTemplate.event_type.asc())
            )
        ).all()
        return [_serialize_template(template) for template in templates]

    async def update_template(
        self,
        *,
        admin: User,
        template_id: uuid.UUID,
        template_text: str,
    ) -> dict[str, Any]:
        normalized_text = template_text.strip()
        if not normalized_text:
            raise ValueError("Текст шаблона не может быть пустым")

        template = await self.db.scalar(
            select(NotificationTemplate).where(NotificationTemplate.id == template_id)
        )
        if template is None:
            raise LookupError("Шаблон не найден")

        old_value = _serialize_template(template)
        template.template_text = normalized_text

        await write_admin_log(
            self.db,
            admin=admin,
            action="update_notification_template",
            entity_type="notification_template",
            entity_id=template.id,
            old_value=old_value,
            new_value={"template_text": normalized_text},
        )
        await self.db.commit()
        await self.db.refresh(template)
        return _serialize_template(template)
