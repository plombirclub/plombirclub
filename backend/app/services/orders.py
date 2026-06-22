import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.rate_limit import hit_rate_limit
from app.core.security import generate_plain_verification_code, hash_verification_code
from app.models.enums import (
    PrizeType,
    RequestStatus,
    VerificationMethod,
    VerificationTargetType,
)
from app.models.prize import Prize
from app.models.prize_distributor import PrizeDistributor
from app.models.request import Request
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.services.notifications import NotificationService
from app.services.points import PointsService
from app.services.users import write_admin_log


MIN_AMOUNT = Decimal("1000")
MAX_AMOUNT = Decimal("10000")
STEP_AMOUNT = Decimal("1000")
SBP_CODE_MAX_ATTEMPTS = 5
SBP_CODE_TTL_SECONDS = 5 * 60
SBP_PENDING_TTL_SECONDS = 5 * 60


def _normalize_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits


def _last_10(phone: str) -> str:
    return _normalize_phone(phone)[-10:]


def _validate_amount(amount_rub: Decimal) -> Decimal:
    amount = _normalize_decimal(amount_rub)
    if amount < MIN_AMOUNT or amount > MAX_AMOUNT:
        raise ValueError("Номинал должен быть от 1000 до 10000 руб.")
    if (amount % STEP_AMOUNT) != Decimal("0.00"):
        raise ValueError("Номинал должен быть кратен 1000 руб.")
    return amount


def _serialize_order(request_row: Request) -> dict[str, Any]:
    prize = request_row.prize
    fulfillment_data = None
    if request_row.fulfillment_data:
        try:
            fulfillment_data = json.loads(request_row.fulfillment_data)
        except json.JSONDecodeError:
            fulfillment_data = {"raw": request_row.fulfillment_data}

    return {
        "id": str(request_row.id),
        "user_id": str(request_row.user_id),
        "prize_id": str(request_row.prize_id),
        "prize_name": prize.name if prize else None,
        "prize_type": prize.type.value if prize else None,
        "status": request_row.status.value,
        "amount_rub": float(_normalize_decimal(request_row.amount_rub)),
        "points_spent": float(_normalize_decimal(request_row.points_spent)),
        "inn": request_row.inn,
        "inn_verified_snapshot": request_row.inn_verified_snapshot,
        "knd_1122035_number_snapshot": request_row.knd_1122035_number_snapshot,
        "self_employed_snapshot": request_row.self_employed_snapshot,
        "phone_verified": request_row.phone_verified,
        "payout_phone": request_row.payout_phone,
        "verification_method": request_row.verification_method.value if request_row.verification_method else None,
        "verification_expires_at": (
            request_row.verification_expires_at.isoformat()
            if request_row.verification_expires_at
            else None
        ),
        "verified_at": request_row.verified_at.isoformat() if request_row.verified_at else None,
        "admin_comment": request_row.admin_comment,
        "fulfillment_data": fulfillment_data,
        "created_at": request_row.created_at.isoformat() if request_row.created_at else None,
        "updated_at": request_row.updated_at.isoformat() if request_row.updated_at else None,
        "user_email": request_row.user.email if getattr(request_row, "user", None) else None,
        "user_full_name": request_row.user.full_name if getattr(request_row, "user", None) else None,
    }


class OrdersService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.points_service = PointsService(db)

    async def create_order(
        self,
        *,
        user: User,
        prize_id: uuid.UUID,
        amount_rub: Decimal,
        payout_phone: str | None,
    ) -> dict[str, Any]:
        amount = _validate_amount(amount_rub)
        prize = await self.db.scalar(select(Prize).where(Prize.id == prize_id).limit(1))
        if prize is None or not prize.is_active:
            raise LookupError("Приз не найден или неактивен")

        if prize.is_system and prize.type == PrizeType.money:
            await self._validate_system_prize_visibility(prize_id=prize.id, user=user)

        if not user.inn or not user.inn_verified_by_admin:
            raise ValueError("Нельзя создать заявку: ИНН не подтвержден администратором")

        is_sbp = prize.type == PrizeType.money
        normalized_payout_phone = None
        phone_matches_profile = False
        if is_sbp:
            if not user.is_self_employed:
                raise ValueError("Для выплаты по СБП требуется подтвержденный статус самозанятого")
            if not user.knd_1122035_number or not user.knd_1122035_document_path:
                raise ValueError("Для выплаты по СБП заполните и загрузите справку КНД 1122035")
            if not payout_phone:
                raise ValueError("Для выплаты по СБП укажите номер телефона")

            normalized_payout_phone = _normalize_phone(payout_phone)
            if len(normalized_payout_phone) != 11 or not normalized_payout_phone.startswith("7"):
                raise ValueError("Некорректный формат телефона СБП")
            if not user.phone:
                raise ValueError("В профиле не заполнен телефон для сравнения")
            phone_matches_profile = _last_10(user.phone) == _last_10(normalized_payout_phone)

        status = (
            RequestStatus.placed
            if (not is_sbp or phone_matches_profile)
            else RequestStatus.verification_pending
        )
        now = datetime.now(UTC)
        request_row = Request(
            user_id=user.id,
            prize_id=prize.id,
            status=status,
            amount_rub=amount,
            points_spent=amount,
            inn=user.inn,
            inn_verified_snapshot=user.inn_verified_by_admin,
            knd_1122035_number_snapshot=user.knd_1122035_number if is_sbp else None,
            self_employed_snapshot=user.is_self_employed,
            phone_verified=(not is_sbp) or phone_matches_profile,
            payout_phone=normalized_payout_phone if is_sbp else None,
            payout_bank_account_snapshot=user.bank_account,
            payout_details_changed_after_request=False,
            verification_expires_at=(now + timedelta(seconds=SBP_PENDING_TTL_SECONDS))
            if status == RequestStatus.verification_pending
            else None,
        )
        self.db.add(request_row)
        await self.db.flush()

        if status == RequestStatus.placed:
            await self.points_service.reserve_points_with_split(
                user_id=user.id,
                request_id=request_row.id,
                amount=amount,
                source="order_create",
                comment="Резервирование баллов под заявку",
                commit=False,
            )

        notification_service = NotificationService(self.db)
        if status == RequestStatus.verification_pending:
            await notification_service.send(
                user_id=user.id,
                event_type="request_phone_verification_required",
                commit=False,
            )
        else:
            await notification_service.send(
                user_id=user.id,
                event_type="request_created",
                commit=False,
            )

        await self.db.commit()
        await self.db.refresh(request_row, attribute_names=["prize"])

        return {
            **_serialize_order(request_row),
            "requires_phone_verification": status == RequestStatus.verification_pending,
        }

    async def confirm_order_code(
        self,
        *,
        user: User,
        request_id: uuid.UUID,
        method: VerificationMethod,
        code: str | None,
    ) -> dict[str, Any]:
        request_row = await self.db.scalar(
            select(Request)
            .options(selectinload(Request.prize))
            .where(
                Request.id == request_id,
                Request.user_id == user.id,
            )
            .limit(1)
        )
        if request_row is None:
            raise LookupError("Заявка не найдена")
        if request_row.status != RequestStatus.verification_pending:
            raise ValueError("Подтверждение кода доступно только для статуса verification_pending")
        if not request_row.payout_phone:
            raise ValueError("В заявке не указан телефон для выплаты")
        await self._cancel_if_verification_expired(request_row=request_row, user_id=user.id)

        if code is None:
            blocked, retry_after = await hit_rate_limit(
                key=f"orders:sbp:send:{user.id}:{request_row.id}",
                limit=SBP_CODE_MAX_ATTEMPTS,
                window_seconds=SBP_CODE_TTL_SECONDS,
            )
            if blocked:
                raise PermissionError(f"Слишком много запросов кода. Повторите через {retry_after} сек.")

            plain_code = generate_plain_verification_code()
            verification = VerificationCode(
                user_id=user.id,
                request_id=request_row.id,
                target_type=VerificationTargetType.request_payout_phone,
                target_value=request_row.payout_phone,
                method=method,
                code_hash=hash_verification_code(plain_code),
                attempts_count=0,
                expires_at=datetime.now(UTC) + timedelta(seconds=SBP_CODE_TTL_SECONDS),
            )
            self.db.add(verification)
            await self.db.commit()

            response_data: dict[str, Any] = {
                "request_id": str(request_row.id),
                "method": method.value,
                "sent_to": request_row.payout_phone,
            }
            if settings.app_env == "development":
                response_data["debug_code"] = plain_code
            return response_data

        blocked, retry_after = await hit_rate_limit(
            key=f"orders:sbp:verify:{user.id}:{request_row.id}",
            limit=SBP_CODE_MAX_ATTEMPTS,
            window_seconds=SBP_CODE_TTL_SECONDS,
        )
        if blocked:
            raise PermissionError(f"Слишком много попыток ввода кода. Повторите через {retry_after} сек.")

        code_row = await self.db.scalar(
            select(VerificationCode)
            .where(
                VerificationCode.user_id == user.id,
                VerificationCode.request_id == request_row.id,
                VerificationCode.method == method,
                VerificationCode.target_type == VerificationTargetType.request_payout_phone,
                VerificationCode.target_value == request_row.payout_phone,
                VerificationCode.verified_at.is_(None),
            )
            .order_by(VerificationCode.created_at.desc())
            .limit(1)
        )
        if code_row is None:
            raise LookupError("Код подтверждения не найден")
        if code_row.expires_at < datetime.now(UTC):
            await self._cancel_if_verification_expired(request_row=request_row, user_id=user.id)
            raise ValueError("Срок действия кода истек")
        if code_row.attempts_count >= SBP_CODE_MAX_ATTEMPTS:
            raise ValueError("Превышено число попыток ввода кода")
        if code_row.code_hash != hash_verification_code(code):
            code_row.attempts_count += 1
            await self.db.commit()
            raise ValueError("Неверный код")

        code_row.verified_at = datetime.now(UTC)
        request_row.status = RequestStatus.placed
        request_row.phone_verified = True
        request_row.verification_method = method
        request_row.verified_at = datetime.now(UTC)
        request_row.verification_expires_at = None

        await self.points_service.reserve_points_with_split(
            user_id=user.id,
            request_id=request_row.id,
            amount=request_row.points_spent,
            source="order_confirm_code",
            comment="Резервирование баллов после подтверждения телефона по коду",
            commit=False,
        )

        notification_service = NotificationService(self.db)
        await notification_service.send(
            user_id=user.id,
            event_type="request_created",
            commit=False,
        )

        await self.db.commit()
        await self.db.refresh(request_row, attribute_names=["prize"])
        return _serialize_order(request_row)

    async def my_orders(self, *, user_id: uuid.UUID, page: int, limit: int) -> dict[str, Any]:
        return await self._list_orders(
            page=page,
            limit=limit,
            where_conditions=[Request.user_id == user_id],
        )

    async def all_orders(
        self,
        *,
        page: int,
        limit: int,
        status_filter: RequestStatus | None,
    ) -> dict[str, Any]:
        conditions: list[Any] = []
        if status_filter:
            conditions.append(Request.status == status_filter)
        return await self._list_orders(
            page=page,
            limit=limit,
            where_conditions=conditions,
        )

    async def update_status(
        self,
        *,
        admin: User,
        request_id: uuid.UUID,
        new_status: RequestStatus,
        admin_comment: str | None,
    ) -> dict[str, Any]:
        request_row = await self.db.scalar(
            select(Request)
            .options(selectinload(Request.prize))
            .where(Request.id == request_id)
            .limit(1)
        )
        if request_row is None:
            raise LookupError("Заявка не найдена")
        if new_status == RequestStatus.fulfilled:
            raise ValueError("Для статуса fulfilled используйте отдельный endpoint /fulfill")
        if request_row.status == RequestStatus.verification_pending:
            await self._cancel_if_verification_expired(
                request_row=request_row,
                user_id=request_row.user_id,
            )

        old_status = request_row.status
        self._validate_status_transition(old_status=old_status, new_status=new_status)
        request_row.status = new_status
        request_row.admin_comment = admin_comment.strip() if admin_comment else None

        if new_status == RequestStatus.rejected and old_status != RequestStatus.verification_pending:
            await self.points_service.refund_reserved_points_for_request(
                request_id=request_row.id,
                user_id=request_row.user_id,
                admin_id=admin.id,
                commit=False,
            )

        await write_admin_log(
            self.db,
            admin=admin,
            action="update_order_status",
            entity_type="request",
            entity_id=request_row.id,
            old_value={"status": old_status.value},
            new_value={"status": new_status.value, "admin_comment": request_row.admin_comment},
        )

        notification_service = NotificationService(self.db)
        if new_status == RequestStatus.confirmed:
            await notification_service.send(
                user_id=request_row.user_id,
                event_type="request_confirmed",
                commit=False,
            )
        elif new_status == RequestStatus.rejected:
            reason = request_row.admin_comment or "не указана"
            await notification_service.send(
                user_id=request_row.user_id,
                event_type="request_rejected",
                reason=reason,
                commit=False,
            )

        await self.db.commit()
        await self.db.refresh(request_row, attribute_names=["prize"])
        return _serialize_order(request_row)

    async def fulfill_order(
        self,
        *,
        admin: User,
        request_id: uuid.UUID,
        certificate_code: str | None,
        certificate_url: str | None,
        certificate_file_url: str | None,
        payout_comment: str | None,
        payout_operation_id: str | None,
    ) -> dict[str, Any]:
        request_row = await self.db.scalar(
            select(Request)
            .options(selectinload(Request.prize))
            .where(Request.id == request_id)
            .limit(1)
        )
        if request_row is None:
            raise LookupError("Заявка не найдена")
        if request_row.status in {RequestStatus.fulfilled, RequestStatus.rejected, RequestStatus.cancelled}:
            raise ValueError("Нельзя выполнить заявку в финальном статусе")
        if request_row.status == RequestStatus.verification_pending:
            raise ValueError("Сначала подтвердите телефон по коду")
        if request_row.status != RequestStatus.processing:
            raise ValueError("Выдача доступна только для заявок в статусе processing")

        prize = request_row.prize
        if prize is None:
            raise LookupError("Приз заявки не найден")

        data: dict[str, Any]
        if prize.type == PrizeType.certificate:
            if not any([certificate_code, certificate_url, certificate_file_url]):
                raise ValueError("Для сертификата укажите промокод, ссылку или файл")
            data = {
                "certificate_code": certificate_code.strip() if certificate_code else None,
                "certificate_url": certificate_url.strip() if certificate_url else None,
                "certificate_file_url": certificate_file_url.strip() if certificate_file_url else None,
            }
        else:
            if not payout_comment and not payout_operation_id:
                raise ValueError("Для СБП укажите комментарий о выплате или номер операции")
            data = {
                "payout_comment": payout_comment.strip() if payout_comment else None,
                "payout_operation_id": payout_operation_id.strip() if payout_operation_id else None,
            }

        request_row.fulfillment_data = json.dumps(data, ensure_ascii=False)
        request_row.status = RequestStatus.fulfilled
        await self.points_service.redeem_reserved_points_for_request(
            request_id=request_row.id,
            user_id=request_row.user_id,
            admin_id=admin.id,
            commit=False,
        )

        await write_admin_log(
            self.db,
            admin=admin,
            action="fulfill_order",
            entity_type="request",
            entity_id=request_row.id,
            new_value={"status": RequestStatus.fulfilled.value, "fulfillment_data": data},
        )

        notification_service = NotificationService(self.db)
        await notification_service.send(
            user_id=request_row.user_id,
            event_type="request_fulfilled",
            commit=False,
        )

        await self.db.commit()
        await self.db.refresh(request_row, attribute_names=["prize"])
        return _serialize_order(request_row)

    async def _list_orders(
        self,
        *,
        page: int,
        limit: int,
        where_conditions: list[Any],
    ) -> dict[str, Any]:
        normalized_page = max(page, 1)
        normalized_limit = min(max(limit, 1), 100)

        count_query = select(func.count(Request.id))
        for condition in where_conditions:
            count_query = count_query.where(condition)
        total_count = int((await self.db.scalar(count_query)) or 0)
        total_pages = max((total_count + normalized_limit - 1) // normalized_limit, 1)
        if normalized_page > total_pages:
            normalized_page = total_pages

        query = select(Request).options(selectinload(Request.prize), selectinload(Request.user))
        for condition in where_conditions:
            query = query.where(condition)

        rows = (
            await self.db.scalars(
                query
                .order_by(Request.created_at.desc(), Request.id.desc())
                .offset((normalized_page - 1) * normalized_limit)
                .limit(normalized_limit)
            )
        ).all()

        return {
            "items": [_serialize_order(row) for row in rows],
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": normalized_page,
                "limit": normalized_limit,
            },
        }

    async def _validate_system_prize_visibility(self, *, prize_id: uuid.UUID, user: User) -> None:
        if user.distributor_id is None:
            raise ValueError("У пользователя не указан дистрибьютор")
        links = (
            await self.db.scalars(
                select(PrizeDistributor).where(PrizeDistributor.prize_id == prize_id)
            )
        ).all()
        if not links:
            return

        visible_for_user = any(
            link.distributor_id == user.distributor_id and link.is_visible for link in links
        )
        if not visible_for_user:
            raise ValueError("СБП-приз недоступен для вашего дистрибьютора")

    def _validate_status_transition(
        self,
        *,
        old_status: RequestStatus,
        new_status: RequestStatus,
    ) -> None:
        if old_status in {RequestStatus.rejected, RequestStatus.fulfilled, RequestStatus.cancelled}:
            raise ValueError("Нельзя изменить финальный статус заявки")
        if old_status == new_status:
            return

        allowed: dict[RequestStatus, set[RequestStatus]] = {
            RequestStatus.verification_pending: {RequestStatus.placed, RequestStatus.cancelled},
            RequestStatus.placed: {RequestStatus.confirmed, RequestStatus.rejected},
            RequestStatus.confirmed: {RequestStatus.processing, RequestStatus.rejected},
            RequestStatus.processing: {RequestStatus.rejected},
        }
        if new_status not in allowed.get(old_status, set()):
            raise ValueError(f"Недопустимый переход статуса: {old_status.value} -> {new_status.value}")

    async def _cancel_if_verification_expired(
        self,
        *,
        request_row: Request,
        user_id: uuid.UUID,
    ) -> None:
        if request_row.status != RequestStatus.verification_pending:
            return
        if request_row.verification_expires_at is None:
            return
        if request_row.verification_expires_at >= datetime.now(UTC):
            return

        request_row.status = RequestStatus.cancelled
        request_row.admin_comment = "Истек срок подтверждения телефона"
        if request_row.points_spent > Decimal("0.00"):
            await self.points_service.refund_reserved_points_for_request(
                user_id=user_id,
                request_id=request_row.id,
                admin_id=None,
                source="order_verification_timeout",
                comment="Автовозврат при истечении подтверждения СБП",
                commit=False,
            )
        await self.db.commit()
        raise ValueError("Срок подтверждения заявки истек. Заявка отменена")
