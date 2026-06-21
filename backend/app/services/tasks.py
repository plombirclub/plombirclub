import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.distributor import Distributor
from app.models.enums import TaskSource, TaskType, UserRole
from app.models.notification import Notification
from app.models.notification_template import NotificationTemplate
from app.models.task import Task
from app.models.task_distributor import TaskDistributor
from app.models.user import User
from app.models.user_actions_log import UserActionsLog
from app.models.user_task_acceptance import UserTaskAcceptance
from app.services.users import write_admin_log


def _current_period_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _validate_period_month(period_month: str) -> str:
    datetime.strptime(period_month, "%Y-%m")
    return period_month


def _serialize_task(
    task: Task,
    *,
    acceptance: UserTaskAcceptance | None = None,
    distributors: list[Distributor] | None = None,
) -> dict[str, Any]:
    distributor_items = distributors
    if distributor_items is None and task.task_distributors:
        distributor_items = [
            link.distributor for link in task.task_distributors if link.distributor is not None
        ]

    return {
        "id": str(task.id),
        "title": task.title,
        "content": task.content,
        "period_month": task.period_month,
        "task_type": task.task_type.value,
        "source": task.source.value,
        "is_published": task.is_published,
        "created_by": str(task.created_by) if task.created_by else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "published_at": task.published_at.isoformat() if task.published_at else None,
        "distributors": [
            {
                "id": str(item.id),
                "name": item.name,
                "is_active": item.is_active,
            }
            for item in (distributor_items or [])
        ],
        "is_accepted": acceptance is not None,
        "accepted_at": acceptance.accepted_at.isoformat() if acceptance and acceptance.accepted_at else None,
    }


class TasksService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_current_task(
        self,
        *,
        user: User,
        period_month: str | None = None,
        task_type: TaskType = TaskType.participation_conditions,
    ) -> dict[str, Any]:
        if user.distributor_id is None:
            raise ValueError("У пользователя не указан дистрибьютор")

        target_period = _validate_period_month(period_month) if period_month else _current_period_month()

        task = await self.db.scalar(
            select(Task)
            .options(
                selectinload(Task.task_distributors).selectinload(TaskDistributor.distributor),
            )
            .join(TaskDistributor, TaskDistributor.task_id == Task.id)
            .where(
                TaskDistributor.distributor_id == user.distributor_id,
                Task.task_type == task_type,
                Task.is_published.is_(True),
                Task.period_month == target_period,
            )
            .order_by(Task.published_at.desc().nullslast(), Task.created_at.desc())
            .limit(1)
        )

        if task is None:
            return {
                "task": None,
                "period_month": target_period,
                "task_type": task_type.value,
                "message": "Условия участия на данный период еще не опубликованы",
            }

        acceptance = await self.db.scalar(
            select(UserTaskAcceptance).where(
                UserTaskAcceptance.user_id == user.id,
                UserTaskAcceptance.task_id == task.id,
            )
        )

        return {
            "task": _serialize_task(task, acceptance=acceptance),
            "period_month": target_period,
            "task_type": task_type.value,
            "message": None,
        }

    async def create_and_publish_task(
        self,
        *,
        admin: User,
        title: str,
        content: str,
        period_month: str,
        task_type: TaskType,
        distributor_ids: list[uuid.UUID],
    ) -> dict[str, Any]:
        if not distributor_ids:
            raise ValueError("Выберите хотя бы одного дистрибьютора")

        normalized_title = title.strip()
        normalized_content = content.strip()
        if not normalized_title:
            raise ValueError("Заголовок задания не может быть пустым")
        if not normalized_content:
            raise ValueError("Содержание задания не может быть пустым")

        target_period = _validate_period_month(period_month)

        distributors = (
            await self.db.scalars(
                select(Distributor).where(Distributor.id.in_(distributor_ids))
            )
        ).all()
        found_ids = {item.id for item in distributors}
        missing_ids = [str(item) for item in distributor_ids if item not in found_ids]
        if missing_ids:
            raise LookupError(f"Дистрибьюторы не найдены: {', '.join(missing_ids)}")

        inactive = [item.name for item in distributors if not item.is_active]
        if inactive:
            raise ValueError(f"Нельзя привязать задание к неактивным дистрибьюторам: {', '.join(inactive)}")

        now = datetime.now(UTC)
        task = Task(
            title=normalized_title,
            content=normalized_content,
            period_month=target_period,
            task_type=task_type,
            source=TaskSource.admin,
            is_published=True,
            created_by=admin.id,
            published_at=now,
        )
        self.db.add(task)
        await self.db.flush()

        for distributor in distributors:
            self.db.add(
                TaskDistributor(
                    task_id=task.id,
                    distributor_id=distributor.id,
                )
            )

        serialized_task = _serialize_task(task, distributors=distributors)

        await write_admin_log(
            self.db,
            admin=admin,
            action="create_task",
            entity_type="task",
            entity_id=task.id,
            new_value=serialized_task,
        )

        notifications_created = await self._notify_distributors_about_task(
            task=task,
            distributor_ids=list(found_ids),
            period_month=target_period,
        )

        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Не удалось создать задание: конфликт данных") from exc

        await self.db.refresh(task)
        serialized_task["id"] = str(task.id)
        serialized_task["created_at"] = task.created_at.isoformat() if task.created_at else None
        serialized_task["published_at"] = task.published_at.isoformat() if task.published_at else None

        return {
            **serialized_task,
            "notifications_created": notifications_created,
        }

    async def accept_task(
        self,
        *,
        user: User,
        task_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        if user.distributor_id is None:
            raise ValueError("У пользователя не указан дистрибьютор")

        task = await self.db.scalar(
            select(Task)
            .join(TaskDistributor, TaskDistributor.task_id == Task.id)
            .where(
                Task.id == task_id,
                Task.is_published.is_(True),
                TaskDistributor.distributor_id == user.distributor_id,
            )
            .limit(1)
        )
        if task is None:
            raise LookupError("Задание не найдено или недоступно для вашего дистрибьютора")

        existing_acceptance = await self.db.scalar(
            select(UserTaskAcceptance).where(
                UserTaskAcceptance.user_id == user.id,
                UserTaskAcceptance.task_id == task.id,
            )
        )
        if existing_acceptance is not None:
            return {
                "task_id": str(task.id),
                "period_month": task.period_month,
                "task_type": task.task_type.value,
                "accepted_at": existing_acceptance.accepted_at.isoformat(),
                "already_accepted": True,
            }

        acceptance = UserTaskAcceptance(user_id=user.id, task_id=task.id)
        self.db.add(acceptance)
        self.db.add(
            UserActionsLog(
                user_id=user.id,
                action="task_accept",
                entity_type="task",
                entity_id=task.id,
                ip_address=ip_address,
            )
        )

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing_acceptance = await self.db.scalar(
                select(UserTaskAcceptance).where(
                    UserTaskAcceptance.user_id == user.id,
                    UserTaskAcceptance.task_id == task.id,
                )
            )
            if existing_acceptance is None:
                raise
            return {
                "task_id": str(task.id),
                "period_month": task.period_month,
                "task_type": task.task_type.value,
                "accepted_at": existing_acceptance.accepted_at.isoformat(),
                "already_accepted": True,
            }

        await self.db.refresh(acceptance)

        return {
            "task_id": str(task.id),
            "period_month": task.period_month,
            "task_type": task.task_type.value,
            "accepted_at": acceptance.accepted_at.isoformat(),
            "already_accepted": False,
        }

    async def _notify_distributors_about_task(
        self,
        *,
        task: Task,
        distributor_ids: list[uuid.UUID],
        period_month: str,
    ) -> int:
        template = await self.db.scalar(
            select(NotificationTemplate).where(NotificationTemplate.event_type == "task_published")
        )
        if template is None:
            return 0

        users = (
            await self.db.scalars(
                select(User).where(
                    User.distributor_id.in_(distributor_ids),
                    User.role == UserRole.user,
                    User.is_active.is_(True),
                )
            )
        ).all()

        message = template.template_text.format(period_month=period_month)
        for user in users:
            self.db.add(
                Notification(
                    user_id=user.id,
                    template_id=template.id,
                    title=task.title,
                    message=message,
                )
            )

        return len(users)
