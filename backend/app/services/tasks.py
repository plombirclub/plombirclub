import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.distributor import Distributor
from app.models.enums import TaskSource, TaskType, UserRole
from app.models.task import Task
from app.models.task_distributor import TaskDistributor
from app.models.user import User
from app.models.user_actions_log import UserActionsLog
from app.models.user_task_acceptance import UserTaskAcceptance
from app.tasks.notifications import send_notification_batch_task
from app.services.users import write_admin_log


def _current_period_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _validate_period_month(period_month: str) -> str:
    datetime.strptime(period_month, "%Y-%m")
    return period_month


def _cover_image_url(path: str | None) -> str | None:
    if not path:
        return None
    normalized = path.replace("\\", "/").lstrip("/")
    if normalized.startswith("uploads/"):
        return f"/{normalized}"
    return f"/uploads/{normalized}"


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
        "cover_image_path": task.cover_image_path,
        "cover_image_url": _cover_image_url(task.cover_image_path),
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

    def _require_distributor(self, user: User) -> None:
        if user.distributor_id is None:
            raise ValueError("У пользователя не указан дистрибьютор")

    async def _acceptance_map(self, user_id: uuid.UUID, task_ids: list[uuid.UUID]) -> dict[uuid.UUID, UserTaskAcceptance]:
        if not task_ids:
            return {}
        acceptances = (
            await self.db.scalars(
                select(UserTaskAcceptance).where(
                    UserTaskAcceptance.user_id == user_id,
                    UserTaskAcceptance.task_id.in_(task_ids),
                )
            )
        ).all()
        return {item.task_id: item for item in acceptances}

    async def list_tasks_for_user(
        self,
        *,
        user: User,
        period_month: str | None = None,
        task_type: TaskType = TaskType.participation_conditions,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        self._require_distributor(user)

        page = max(page, 1)
        limit = min(max(limit, 1), 100)

        conditions = [
            TaskDistributor.distributor_id == user.distributor_id,
            Task.task_type == task_type,
            Task.is_published.is_(True),
        ]
        if period_month:
            conditions.append(Task.period_month == _validate_period_month(period_month))

        total_count = await self.db.scalar(
            select(func.count(Task.id))
            .select_from(Task)
            .join(TaskDistributor, TaskDistributor.task_id == Task.id)
            .where(*conditions)
        )
        total_count = int(total_count or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        tasks = (
            await self.db.scalars(
                select(Task)
                .options(
                    selectinload(Task.task_distributors).selectinload(TaskDistributor.distributor),
                )
                .join(TaskDistributor, TaskDistributor.task_id == Task.id)
                .where(*conditions)
                .order_by(Task.published_at.desc().nullslast(), Task.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        acceptance_map = await self._acceptance_map(user.id, [task.id for task in tasks])

        return {
            "items": [
                _serialize_task(task, acceptance=acceptance_map.get(task.id))
                for task in tasks
            ],
            "period_month": period_month,
            "task_type": task_type.value,
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def list_tasks_admin(
        self,
        *,
        period_month: str | None = None,
        task_type: TaskType = TaskType.participation_conditions,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)

        conditions = [Task.task_type == task_type]
        if period_month:
            conditions.append(Task.period_month == _validate_period_month(period_month))

        total_count = await self.db.scalar(
            select(func.count(Task.id)).where(*conditions)
        )
        total_count = int(total_count or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        tasks = (
            await self.db.scalars(
                select(Task)
                .options(
                    selectinload(Task.task_distributors).selectinload(TaskDistributor.distributor),
                )
                .where(*conditions)
                .order_by(Task.published_at.desc().nullslast(), Task.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        return {
            "items": [_serialize_task(task) for task in tasks],
            "period_month": period_month,
            "task_type": task_type.value,
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def get_task_for_user(
        self,
        *,
        user: User,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        self._require_distributor(user)

        task = await self.db.scalar(
            select(Task)
            .options(
                selectinload(Task.task_distributors).selectinload(TaskDistributor.distributor),
            )
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

        acceptance = await self.db.scalar(
            select(UserTaskAcceptance).where(
                UserTaskAcceptance.user_id == user.id,
                UserTaskAcceptance.task_id == task.id,
            )
        )
        return {"task": _serialize_task(task, acceptance=acceptance)}

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
        cover_image_path: str | None = None,
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
            cover_image_path=cover_image_path,
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

        notifications_queued = 0

        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Не удалось создать задание: конфликт данных") from exc

        notifications_queued = await self._queue_distributors_notification(
            task=task,
            distributor_ids=list(found_ids),
            period_month=target_period,
        )

        await self.db.refresh(task)
        serialized_task["id"] = str(task.id)
        serialized_task["created_at"] = task.created_at.isoformat() if task.created_at else None
        serialized_task["published_at"] = task.published_at.isoformat() if task.published_at else None

        return {
            **serialized_task,
            "notifications_queued": notifications_queued,
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

    async def _queue_distributors_notification(
        self,
        *,
        task: Task,
        distributor_ids: list[uuid.UUID],
        period_month: str,
    ) -> int:
        users = (
            await self.db.scalars(
                select(User).where(
                    User.distributor_id.in_(distributor_ids),
                    User.role == UserRole.user,
                    User.is_active.is_(True),
                )
            )
        ).all()
        if not users:
            return 0

        items = [
            {
                "user_id": str(user.id),
                "event_type": "task_published",
                "title": task.title,
                "period_month": period_month,
            }
            for user in users
        ]
        send_notification_batch_task.delay(items=items)
        return len(users)
