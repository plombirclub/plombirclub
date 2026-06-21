import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable

from sqlalchemy import Select, func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import PointsLedgerStatus, PointsOperationType, TaskType
from app.models.points_ledger import PointsLedger
from app.models.points_operations_log import PointsOperationsLog
from app.models.task import Task
from app.models.task_distributor import TaskDistributor
from app.models.user import User
from app.models.user_actions_log import UserActionsLog
from app.models.user_task_acceptance import UserTaskAcceptance

logger = logging.getLogger(__name__)

MAX_DEADLOCK_RETRIES = 3
DEADLOCK_RETRY_DELAY_SECONDS = 0.1


@dataclass(slots=True)
class PaginationParams:
    page: int = 1
    limit: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"


def _normalize_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _is_deadlock_error(exc: DBAPIError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return "deadlock" in message or "lock timeout" in message


def _current_period_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _validate_period_month(period_month: str) -> str:
    datetime.strptime(period_month, "%Y-%m")
    return period_month


class PointsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_balance(self, *, user_id: uuid.UUID) -> dict[str, Any]:
        rows = (
            await self.db.execute(
                select(
                    PointsLedger.status,
                    func.coalesce(func.sum(PointsLedger.amount), 0).label("total"),
                )
                .where(PointsLedger.user_id == user_id)
                .group_by(PointsLedger.status)
            )
        ).all()

        totals: dict[PointsLedgerStatus, Decimal] = {
            status: Decimal("0.00") for status in PointsLedgerStatus
        }
        for status, total in rows:
            totals[status] = _normalize_decimal(total)

        available = totals[PointsLedgerStatus.active]
        pending_redemption = totals[PointsLedgerStatus.pending_redemption]
        pending_activation = totals[PointsLedgerStatus.pending]

        return {
            "available": float(available),
            "pending_activation": float(pending_activation),
            "pending_redemption": float(pending_redemption),
            "inactive": float(totals[PointsLedgerStatus.inactive]),
            "redeemed": float(totals[PointsLedgerStatus.redeemed]),
            "total": float(_normalize_decimal(sum(totals.values(), Decimal("0.00")))),
        }

    async def get_history(
        self,
        *,
        user_id: uuid.UUID,
        pagination: PaginationParams,
    ) -> dict[str, Any]:
        page = max(pagination.page, 1)
        limit = min(max(pagination.limit, 1), 100)

        sortable_columns = {
            "created_at": PointsLedger.created_at,
            "updated_at": PointsLedger.updated_at,
            "period_month": PointsLedger.period_month,
            "amount": PointsLedger.amount,
            "status": PointsLedger.status,
        }
        sort_column = sortable_columns.get(pagination.sort_by, PointsLedger.created_at)
        sort_expr = sort_column.asc() if pagination.sort_order.lower() == "asc" else sort_column.desc()

        total_count = await self.db.scalar(
            select(func.count(PointsLedger.id)).where(PointsLedger.user_id == user_id)
        )
        total_count = int(total_count or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        items = (
            await self.db.scalars(
                select(PointsLedger)
                .where(PointsLedger.user_id == user_id)
                .order_by(sort_expr, PointsLedger.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        return {
            "items": [
                {
                    "id": str(item.id),
                    "amount": float(_normalize_decimal(item.amount)),
                    "status": item.status.value,
                    "source": item.source,
                    "request_id": str(item.request_id) if item.request_id else None,
                    "period_month": item.period_month,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                }
                for item in items
            ],
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def save_participation_consent(
        self,
        *,
        user: User,
        period_month: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        if user.distributor_id is None:
            raise ValueError("У пользователя не указан дистрибьютор")

        target_period = _validate_period_month(period_month) if period_month else _current_period_month()
        task = await self._find_participation_task(
            distributor_id=user.distributor_id,
            period_month=target_period,
        )
        if task is None:
            raise LookupError("Опубликованные условия участия для выбранного периода не найдены")

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
                "accepted_at": existing_acceptance.accepted_at.isoformat(),
                "already_accepted": True,
            }

        acceptance = UserTaskAcceptance(user_id=user.id, task_id=task.id)
        self.db.add(acceptance)
        self.db.add(
            UserActionsLog(
                user_id=user.id,
                action="points_participation_consent",
                entity_type="task",
                entity_id=task.id,
                ip_address=ip_address,
            )
        )
        await self.db.commit()
        await self.db.refresh(acceptance)

        return {
            "task_id": str(task.id),
            "period_month": task.period_month,
            "accepted_at": acceptance.accepted_at.isoformat(),
            "already_accepted": False,
        }

    async def activate_pending_points(
        self,
        *,
        user_id: uuid.UUID,
        period_month: str | None = None,
        source: str = "user_points_activate",
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        target_period = _validate_period_month(period_month) if period_month else None

        async def _activate_once() -> dict[str, Any]:
            await self._lock_user(user_id=user_id)

            query = (
                select(PointsLedger)
                .where(
                    PointsLedger.user_id == user_id,
                    PointsLedger.status == PointsLedgerStatus.pending,
                )
                .order_by(PointsLedger.created_at.asc(), PointsLedger.id.asc())
                .with_for_update()
            )
            if target_period:
                query = query.where(PointsLedger.period_month == target_period)

            entries = (await self.db.scalars(query)).all()
            if not entries:
                return {
                    "activated_count": 0,
                    "activated_amount": 0.0,
                    "period_month": target_period,
                }

            total_amount = Decimal("0.00")
            now = datetime.now(UTC)
            for entry in entries:
                entry.status = PointsLedgerStatus.active
                total_amount += entry.amount
                self.db.add(
                    PointsOperationsLog(
                        user_id=user_id,
                        request_id=entry.request_id,
                        amount=entry.amount,
                        operation_type=PointsOperationType.activation,
                        source=source,
                        admin_id=None,
                        comment=f"Активация баллов за период {entry.period_month or 'unknown'}",
                    )
                )

            self.db.add(
                UserActionsLog(
                    user_id=user_id,
                    action="points_activate",
                    entity_type="points",
                    entity_id=None,
                    ip_address=ip_address,
                )
            )
            await self.db.commit()

            return {
                "activated_count": len(entries),
                "activated_amount": float(_normalize_decimal(total_amount)),
                "period_month": target_period,
                "activated_at": now.isoformat(),
            }

        return await self._run_with_deadlock_retry(_activate_once)

    async def reserve_points_with_split(
        self,
        *,
        user_id: uuid.UUID,
        amount: Decimal,
        request_id: uuid.UUID,
        source: str,
        comment: str | None = None,
    ) -> list[PointsLedger]:
        """
        Вспомогательный метод для следующих этапов:
        резервирует активные баллы и при необходимости делит записи.
        """
        required_amount = _normalize_decimal(amount)
        if required_amount <= Decimal("0.00"):
            raise ValueError("Сумма для резервирования должна быть больше нуля")

        async def _reserve_once() -> list[PointsLedger]:
            await self._lock_user(user_id=user_id)

            active_entries = (
                await self.db.scalars(
                    select(PointsLedger)
                    .where(
                        PointsLedger.user_id == user_id,
                        PointsLedger.status == PointsLedgerStatus.active,
                    )
                    .order_by(PointsLedger.created_at.asc(), PointsLedger.id.asc())
                    .with_for_update()
                )
            ).all()

            available = _normalize_decimal(
                sum((entry.amount for entry in active_entries), Decimal("0.00"))
            )
            if available < required_amount:
                raise ValueError(
                    f"Недостаточно активных баллов. Доступно: {available}, требуется: {required_amount}"
                )

            reserved_entries: list[PointsLedger] = []
            remaining = required_amount

            for entry in active_entries:
                if remaining <= Decimal("0.00"):
                    break
                entry_amount = _normalize_decimal(entry.amount)
                if entry_amount <= remaining:
                    entry.status = PointsLedgerStatus.pending_redemption
                    entry.request_id = request_id
                    reserved_entries.append(entry)
                    remaining -= entry_amount
                    continue

                # Частичное резервирование: исходная запись остаётся active,
                # а зарезервированная часть создаётся отдельной записью.
                reserved_part = _normalize_decimal(remaining)
                entry.amount = _normalize_decimal(entry_amount - reserved_part)
                split_entry = PointsLedger(
                    user_id=entry.user_id,
                    amount=reserved_part,
                    status=PointsLedgerStatus.pending_redemption,
                    source=entry.source,
                    request_id=request_id,
                    period_month=entry.period_month,
                )
                self.db.add(split_entry)
                reserved_entries.append(split_entry)
                remaining = Decimal("0.00")

            if remaining > Decimal("0.00"):
                raise RuntimeError("Не удалось полностью зарезервировать требуемую сумму баллов")

            for entry in reserved_entries:
                self.db.add(
                    PointsOperationsLog(
                        user_id=user_id,
                        request_id=request_id,
                        amount=entry.amount,
                        operation_type=PointsOperationType.reserve,
                        source=source,
                        admin_id=None,
                        comment=comment,
                    )
                )
            await self.db.commit()

            return reserved_entries

        return await self._run_with_deadlock_retry(_reserve_once)

    async def list_pending_activation(
        self,
        *,
        pagination: PaginationParams,
        period_month: str | None = None,
    ) -> dict[str, Any]:
        page = max(pagination.page, 1)
        limit = min(max(pagination.limit, 1), 100)
        target_period = _validate_period_month(period_month) if period_month else None

        sum_expr = func.coalesce(func.sum(PointsLedger.amount), 0).label("pending_amount")
        count_expr = func.count(PointsLedger.id).label("pending_records")

        base_query: Select[Any] = (
            select(User, sum_expr, count_expr)
            .join(PointsLedger, PointsLedger.user_id == User.id)
            .options(selectinload(User.distributor))
            .where(PointsLedger.status == PointsLedgerStatus.pending)
            .group_by(User.id)
        )
        if target_period:
            base_query = base_query.where(PointsLedger.period_month == target_period)

        order_by_map = {
            "pending_amount": sum_expr,
            "pending_records": count_expr,
            "created_at": User.created_at,
            "email": User.email,
        }
        order_column = order_by_map.get(pagination.sort_by, sum_expr)
        order_expr = order_column.asc() if pagination.sort_order.lower() == "asc" else order_column.desc()

        count_subquery = base_query.subquery()
        total_count = await self.db.scalar(select(func.count()).select_from(count_subquery))
        total_count = int(total_count or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages

        rows = (
            await self.db.execute(
                base_query.order_by(order_expr).offset((page - 1) * limit).limit(limit)
            )
        ).all()

        return {
            "items": [
                {
                    "user_id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "distributor_id": str(user.distributor_id) if user.distributor_id else None,
                    "distributor_name": user.distributor.name if user.distributor else None,
                    "pending_amount": float(_normalize_decimal(pending_amount)),
                    "pending_records": int(pending_records),
                }
                for user, pending_amount, pending_records in rows
            ],
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def _find_participation_task(
        self,
        *,
        distributor_id: uuid.UUID,
        period_month: str,
    ) -> Task | None:
        return await self.db.scalar(
            select(Task)
            .join(TaskDistributor, TaskDistributor.task_id == Task.id)
            .where(
                TaskDistributor.distributor_id == distributor_id,
                Task.task_type == TaskType.participation_conditions,
                Task.is_published.is_(True),
                Task.period_month == period_month,
            )
            .order_by(Task.published_at.desc().nullslast(), Task.created_at.desc())
            .limit(1)
        )

    async def _lock_user(self, *, user_id: uuid.UUID) -> None:
        user = await self.db.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .limit(1)
        )
        if user is None:
            raise LookupError("Пользователь не найден")

    async def _run_with_deadlock_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
    ) -> Any:
        for attempt in range(1, MAX_DEADLOCK_RETRIES + 1):
            try:
                return await operation()
            except DBAPIError as exc:
                await self.db.rollback()
                if attempt < MAX_DEADLOCK_RETRIES and _is_deadlock_error(exc):
                    logger.warning(
                        "Deadlock detected in points transaction. Attempt %s/%s",
                        attempt,
                        MAX_DEADLOCK_RETRIES,
                    )
                    await asyncio.sleep(DEADLOCK_RETRY_DELAY_SECONDS)
                    continue
                raise
