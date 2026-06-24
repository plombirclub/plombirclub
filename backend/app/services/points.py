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
from app.models.notification import Notification
from app.models.notification_template import NotificationTemplate
from app.utils.datetime_msk import compute_activation_deadline, is_points_deadline_check_day, now_msk
from app.models.points_ledger import PointsLedger
from app.models.points_operations_log import PointsOperationsLog
from app.models.points_overwritten_log import PointsOverwrittenLog
from app.models.task import Task
from app.models.task_distributor import TaskDistributor
from app.models.user import User
from app.models.user_actions_log import UserActionsLog
from app.models.user_task_acceptance import UserTaskAcceptance
from app.services.notifications import NotificationService

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


def _previous_period_month() -> str:
    now = now_msk()
    if now.month == 1:
        return f"{now.year - 1}-12"
    return f"{now.year:04d}-{now.month - 1:02d}"


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

    async def get_overview(self, *, user_id: uuid.UUID) -> dict[str, Any]:
        balance = await self.get_balance(user_id=user_id)

        status_rows = [
            {
                "status": "accrued",
                "status_label": "НАЧИСЛЕННО",
                "amount": balance["total"],
                "comment": "количество заработанных баллов",
            },
            {
                "status": "active",
                "status_label": "АКТИВИРОВАНО",
                "amount": balance["available"],
                "comment": "эти баллы можно тратить - создайте заявку на обмен в разделе Каталог призов",
            },
            {
                "status": "pending_redemption",
                "status_label": "ЗАРЕЗЕРВИРОВАНО",
                "amount": balance["pending_redemption"],
                "comment": "сейчас в заявках на обмен, заявки утверждаются в течении 5 рабочих дней",
            },
            {
                "status": "pending",
                "status_label": "ОЖИДАЮТ АКТИВАЦИИ",
                "amount": balance["pending_activation"],
                "comment": "баллы необходимо активировать с 1-е по 15-е число каждого месяца",
            },
            {
                "status": "redeemed",
                "status_label": "ПОГАШЕНО",
                "amount": balance["redeemed"],
                "comment": "списанные баллы по утверждённым заявкам на обмен",
            },
        ]

        pending_by_period = (
            await self.db.execute(
                select(
                    PointsLedger.period_month,
                    func.coalesce(func.sum(PointsLedger.amount), 0).label("pending_amount"),
                    func.count(PointsLedger.id).label("pending_records"),
                )
                .where(
                    PointsLedger.user_id == user_id,
                    PointsLedger.status == PointsLedgerStatus.pending,
                )
                .group_by(PointsLedger.period_month)
                .order_by(PointsLedger.period_month.desc().nullslast())
            )
        ).all()

        activation_items: list[dict[str, Any]] = []
        for period_month, pending_amount, pending_records in pending_by_period:
            deadline_at: str | None = None
            notification_at: str | None = None
            if period_month:
                notify_dt = await self._get_activation_notification_at(
                    user_id=user_id,
                    period_month=period_month,
                )
                # Задача в ЛК появляется только после ручной отправки админом.
                if notify_dt is None:
                    continue
                deadline = compute_activation_deadline(period_month, notify_dt)
                deadline_at = deadline.isoformat()
                notification_at = notify_dt.isoformat()

            activation_items.append(
                {
                    "period_month": period_month,
                    "amount": float(_normalize_decimal(pending_amount)),
                    "records_count": int(pending_records),
                    "deadline_at": deadline_at,
                    "notification_at": notification_at,
                }
            )

        activation_task: dict[str, Any] | None = None
        if activation_items:
            with_deadline = [item for item in activation_items if item["deadline_at"]]
            if with_deadline:
                activation_task = min(with_deadline, key=lambda item: item["deadline_at"])
            else:
                activation_task = activation_items[0]

        return {
            "status_rows": status_rows,
            "activation_task": activation_task,
            "activation_items": activation_items,
            "updated_at": datetime.now(UTC).isoformat(),
        }

    async def send_activation_task_for_previous_month(
        self,
        *,
        user_id: uuid.UUID,
        admin_id: uuid.UUID | None = None,
        period_month: str | None = None,
    ) -> dict[str, Any]:
        target_period = _validate_period_month(period_month) if period_month else _previous_period_month()
        expected_period = _previous_period_month()
        if target_period != expected_period:
            raise ValueError(
                f"Отправка задачи доступна только за предыдущий месяц ({expected_period})"
            )

        user = await self.db.scalar(select(User).where(User.id == user_id).limit(1))
        if user is None:
            raise LookupError("Пользователь не найден")
        if user.role.value != "user":
            raise ValueError("Задача активации отправляется только участникам")

        pending_amount = await self.db.scalar(
            select(func.coalesce(func.sum(PointsLedger.amount), 0))
            .where(
                PointsLedger.user_id == user_id,
                PointsLedger.status == PointsLedgerStatus.pending,
                PointsLedger.period_month == target_period,
            )
        )
        pending_records = await self.db.scalar(
            select(func.count(PointsLedger.id))
            .where(
                PointsLedger.user_id == user_id,
                PointsLedger.status == PointsLedgerStatus.pending,
                PointsLedger.period_month == target_period,
            )
        )
        pending_amount = _normalize_decimal(pending_amount or Decimal("0.00"))
        pending_records = int(pending_records or 0)
        if pending_records == 0:
            raise ValueError("За предыдущий месяц нет pending-баллов для отправки задачи")

        existing_notification_at = await self._get_activation_notification_at(
            user_id=user_id,
            period_month=target_period,
        )
        if existing_notification_at is not None:
            deadline = compute_activation_deadline(target_period, existing_notification_at)
            return {
                "already_sent": True,
                "user_id": str(user_id),
                "period_month": target_period,
                "pending_amount": float(pending_amount),
                "pending_records": pending_records,
                "notification_sent_at": existing_notification_at.isoformat(),
                "activation_deadline": deadline.isoformat(),
                "admin_id": str(admin_id) if admin_id else None,
            }

        notification = await NotificationService(self.db).send(
            user_id=user_id,
            event_type="points_activation",
            commit=False,
            period_month=target_period,
        )
        if notification is None:
            raise LookupError("Шаблон уведомления points_activation не найден")

        await self.db.flush()
        sent_at = notification.created_at or datetime.now(UTC)
        deadline = compute_activation_deadline(target_period, sent_at)
        await self.db.commit()

        return {
            "already_sent": False,
            "user_id": str(user_id),
            "period_month": target_period,
            "pending_amount": float(pending_amount),
            "pending_records": pending_records,
            "notification_sent_at": sent_at.isoformat(),
            "activation_deadline": deadline.isoformat(),
            "admin_id": str(admin_id) if admin_id else None,
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

    async def admin_activate_points(
        self,
        *,
        user_id: uuid.UUID,
        admin_id: uuid.UUID,
        period_month: str | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Ручная активация баллов администратором (inactive или pending → active)."""
        target_period = _validate_period_month(period_month) if period_month else None
        admin_comment = (comment or "").strip() or "Ручная активация баллов администратором"

        async def _activate_once() -> dict[str, Any]:
            await self._lock_user(user_id=user_id)

            query = (
                select(PointsLedger)
                .where(
                    PointsLedger.user_id == user_id,
                    PointsLedger.status.in_(
                        [PointsLedgerStatus.inactive, PointsLedgerStatus.pending]
                    ),
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
                        source="admin_manual_activation",
                        admin_id=admin_id,
                        comment=f"{admin_comment} (период {entry.period_month or 'unknown'})",
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
        commit: bool = True,
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
            if commit:
                await self.db.commit()

            return reserved_entries

        return await self._run_with_deadlock_retry(_reserve_once)

    async def refund_reserved_points_for_request(
        self,
        *,
        user_id: uuid.UUID,
        request_id: uuid.UUID,
        admin_id: uuid.UUID | None,
        source: str = "order_rejected",
        comment: str | None = "Возврат баллов при отклонении заявки",
        commit: bool = True,
    ) -> list[PointsLedger]:
        async def _refund_once() -> list[PointsLedger]:
            await self._lock_user(user_id=user_id)

            entries = (
                await self.db.scalars(
                    select(PointsLedger)
                    .where(
                        PointsLedger.user_id == user_id,
                        PointsLedger.request_id == request_id,
                        PointsLedger.status == PointsLedgerStatus.pending_redemption,
                    )
                    .order_by(PointsLedger.created_at.asc(), PointsLedger.id.asc())
                    .with_for_update()
                )
            ).all()

            for entry in entries:
                entry.status = PointsLedgerStatus.active
                entry.request_id = None
                self.db.add(
                    PointsOperationsLog(
                        user_id=user_id,
                        request_id=request_id,
                        amount=entry.amount,
                        operation_type=PointsOperationType.refund,
                        source=source,
                        admin_id=admin_id,
                        comment=comment,
                    )
                )
            if commit:
                await self.db.commit()
            return entries

        return await self._run_with_deadlock_retry(_refund_once)

    async def redeem_reserved_points_for_request(
        self,
        *,
        user_id: uuid.UUID,
        request_id: uuid.UUID,
        admin_id: uuid.UUID | None,
        source: str = "order_fulfilled",
        comment: str | None = "Списание баллов по выполненной заявке",
        commit: bool = True,
    ) -> list[PointsLedger]:
        async def _redeem_once() -> list[PointsLedger]:
            await self._lock_user(user_id=user_id)

            entries = (
                await self.db.scalars(
                    select(PointsLedger)
                    .where(
                        PointsLedger.user_id == user_id,
                        PointsLedger.request_id == request_id,
                        PointsLedger.status == PointsLedgerStatus.pending_redemption,
                    )
                    .order_by(PointsLedger.created_at.asc(), PointsLedger.id.asc())
                    .with_for_update()
                )
            ).all()
            if not entries:
                raise ValueError("Нет зарезервированных баллов для выдачи заявки")

            for entry in entries:
                entry.status = PointsLedgerStatus.redeemed
                self.db.add(
                    PointsOperationsLog(
                        user_id=user_id,
                        request_id=request_id,
                        amount=entry.amount,
                        operation_type=PointsOperationType.redeem,
                        source=source,
                        admin_id=admin_id,
                        comment=comment,
                    )
                )
            if commit:
                await self.db.commit()
            return entries

        return await self._run_with_deadlock_retry(_redeem_once)

    async def upsert_import_points_entry(
        self,
        *,
        user_id: uuid.UUID,
        source: str,
        amount: Decimal,
        status: PointsLedgerStatus,
        period_month: str,
        admin_id: uuid.UUID | None,
        import_file_name: str | None,
        import_row_number: int | None,
        create_comment: str,
        overwrite_comment: str,
        commit: bool = True,
    ) -> str:
        normalized_amount = _normalize_decimal(amount)

        async def _upsert_once() -> str:
            existing_entry = await self.db.scalar(
                select(PointsLedger)
                .where(
                    PointsLedger.user_id == user_id,
                    PointsLedger.source == source,
                )
                .with_for_update()
            )
            if existing_entry is None:
                self.db.add(
                    PointsLedger(
                        user_id=user_id,
                        amount=normalized_amount,
                        status=status,
                        source=source,
                        request_id=None,
                        period_month=period_month,
                    )
                )
                self.db.add(
                    PointsOperationsLog(
                        user_id=user_id,
                        request_id=None,
                        amount=normalized_amount,
                        operation_type=PointsOperationType.import_,
                        source=source,
                        admin_id=admin_id,
                        comment=create_comment,
                    )
                )
                if commit:
                    await self.db.commit()
                return "created"

            if (
                _normalize_decimal(existing_entry.amount) == normalized_amount
                and existing_entry.status == status
                and existing_entry.period_month == period_month
            ):
                return "duplicate"

            self.db.add(
                PointsOverwrittenLog(
                    user_id=user_id,
                    period_month=existing_entry.period_month or period_month,
                    old_amount=_normalize_decimal(existing_entry.amount),
                    new_amount=normalized_amount,
                    old_status=existing_entry.status.value,
                    new_status=status.value,
                    import_file_name=import_file_name,
                    import_row_number=import_row_number,
                    changed_by=admin_id,
                    reason="Повторный импорт строки продаж с изменением данных",
                )
            )
            existing_entry.amount = normalized_amount
            existing_entry.status = status
            existing_entry.period_month = period_month
            self.db.add(
                PointsOperationsLog(
                    user_id=user_id,
                    request_id=None,
                    amount=normalized_amount,
                    operation_type=PointsOperationType.import_,
                    source=source,
                    admin_id=admin_id,
                    comment=overwrite_comment,
                )
            )
            if commit:
                await self.db.commit()
            return "overwritten"

        return await self._run_with_deadlock_retry(_upsert_once)

    async def expire_overdue_pending_points(self) -> dict[str, Any]:
        """Переводит просроченные pending-баллы в inactive (запуск с 16 по 21 число, 00:01 МСК)."""
        if not is_points_deadline_check_day():
            return {
                "skipped": True,
                "reason": "outside_check_window",
                "expired_users": 0,
                "expired_records": 0,
                "expired_amount": 0.0,
            }

        now = now_msk()
        groups = (
            await self.db.execute(
                select(PointsLedger.user_id, PointsLedger.period_month)
                .where(
                    PointsLedger.status == PointsLedgerStatus.pending,
                    PointsLedger.period_month.is_not(None),
                )
                .group_by(PointsLedger.user_id, PointsLedger.period_month)
            )
        ).all()

        expired_users = 0
        expired_records = 0
        expired_amount = Decimal("0.00")

        for user_id, period_month in groups:
            if not period_month:
                continue
            notification_at = await self._resolve_activation_notification_at(
                user_id=user_id,
                period_month=period_month,
            )
            deadline = compute_activation_deadline(period_month, notification_at)
            if now <= deadline:
                continue

            result = await self._expire_pending_for_user_period(
                user_id=user_id,
                period_month=period_month,
                deadline=deadline,
            )
            if result["expired_records"] > 0:
                expired_users += 1
                expired_records += result["expired_records"]
                expired_amount += Decimal(str(result["expired_amount"]))

        await self.db.commit()
        return {
            "skipped": False,
            "expired_users": expired_users,
            "expired_records": expired_records,
            "expired_amount": float(_normalize_decimal(expired_amount)),
            "checked_at": now.isoformat(),
        }

    async def _get_activation_notification_at(
        self,
        *,
        user_id: uuid.UUID,
        period_month: str,
    ) -> datetime | None:
        return await self.db.scalar(
            select(func.min(Notification.created_at))
            .join(NotificationTemplate, Notification.template_id == NotificationTemplate.id)
            .where(
                Notification.user_id == user_id,
                NotificationTemplate.event_type == "points_activation",
                Notification.message.contains(period_month),
            )
        )

    async def _resolve_activation_notification_at(
        self,
        *,
        user_id: uuid.UUID,
        period_month: str,
    ) -> datetime:
        notified_at = await self._get_activation_notification_at(
            user_id=user_id,
            period_month=period_month,
        )
        if notified_at is not None:
            return notified_at

        fallback = await self.db.scalar(
            select(func.min(PointsLedger.created_at)).where(
                PointsLedger.user_id == user_id,
                PointsLedger.period_month == period_month,
                PointsLedger.status == PointsLedgerStatus.pending,
            )
        )
        return fallback or datetime.now(UTC)

    async def _expire_pending_for_user_period(
        self,
        *,
        user_id: uuid.UUID,
        period_month: str,
        deadline: datetime,
    ) -> dict[str, Any]:
        async def _expire_once() -> dict[str, Any]:
            await self._lock_user(user_id=user_id)
            entries = (
                await self.db.scalars(
                    select(PointsLedger)
                    .where(
                        PointsLedger.user_id == user_id,
                        PointsLedger.period_month == period_month,
                        PointsLedger.status == PointsLedgerStatus.pending,
                    )
                    .with_for_update()
                )
            ).all()
            if not entries:
                return {"expired_records": 0, "expired_amount": 0.0}

            total_amount = Decimal("0.00")
            for entry in entries:
                entry.status = PointsLedgerStatus.inactive
                total_amount += entry.amount
                self.db.add(
                    PointsOperationsLog(
                        user_id=user_id,
                        request_id=entry.request_id,
                        amount=entry.amount,
                        operation_type=PointsOperationType.manual_adjustment,
                        source="scheduler_points_deadline",
                        admin_id=None,
                        comment=(
                            f"Автоматическая просрочка активации за период {period_month} "
                            f"(дедлайн {deadline.astimezone(UTC).isoformat()})"
                        ),
                    )
                )

            self.db.add(
                UserActionsLog(
                    user_id=user_id,
                    action="points_activation_expired",
                    entity_type="points",
                    entity_id=None,
                    ip_address=None,
                )
            )
            return {
                "expired_records": len(entries),
                "expired_amount": float(_normalize_decimal(total_amount)),
            }

        return await self._run_with_deadlock_retry(_expire_once)

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

        notification_map: dict[uuid.UUID, datetime] = {}
        if target_period and rows:
            user_ids = [user.id for user, _, _ in rows]
            sent_rows = (
                await self.db.execute(
                    select(Notification.user_id, func.min(Notification.created_at))
                    .join(NotificationTemplate, Notification.template_id == NotificationTemplate.id)
                    .where(
                        Notification.user_id.in_(user_ids),
                        NotificationTemplate.event_type == "points_activation",
                        Notification.message.contains(target_period),
                    )
                    .group_by(Notification.user_id)
                )
            ).all()
            notification_map = {user_id: sent_at for user_id, sent_at in sent_rows}

        items = []
        for user, pending_amount, pending_records in rows:
            sent_at = notification_map.get(user.id)
            deadline = (
                compute_activation_deadline(target_period, sent_at).isoformat()
                if target_period and sent_at
                else None
            )
            items.append(
                {
                    "user_id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "distributor_id": str(user.distributor_id) if user.distributor_id else None,
                    "distributor_name": user.distributor.name if user.distributor else None,
                    "pending_amount": float(_normalize_decimal(pending_amount)),
                    "pending_records": int(pending_records),
                    "activation_task_sent": sent_at is not None,
                    "activation_task_sent_at": sent_at.isoformat() if sent_at else None,
                    "activation_deadline": deadline,
                }
            )

        return {
            "items": items,
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
