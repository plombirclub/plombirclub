from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RequestStatus, SystemLogLevel
from app.models.request import Request
from app.models.system_log import SystemLog
from app.models.verification_code import VerificationCode
from app.services.points import PointsService


class VerificationCleanupService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.points_service = PointsService(db)

    async def expire_stale_records(self) -> dict[str, int]:
        now = datetime.now(UTC)
        deleted_codes = await self._delete_expired_codes(now=now)
        cancelled_orders = await self._cancel_expired_verification_orders(now=now)
        if deleted_codes or cancelled_orders:
            self.db.add(
                SystemLog(
                    level=SystemLogLevel.INFO,
                    source="scheduler",
                    message="Очистка просроченных кодов верификации",
                    details=(
                        f'{{"deleted_codes": {deleted_codes}, "cancelled_orders": {cancelled_orders}}}'
                    ),
                )
            )
        await self.db.commit()
        return {
            "deleted_codes": deleted_codes,
            "cancelled_orders": cancelled_orders,
        }

    async def _delete_expired_codes(self, *, now: datetime) -> int:
        result = await self.db.execute(
            delete(VerificationCode).where(
                VerificationCode.verified_at.is_(None),
                VerificationCode.expires_at < now,
            )
        )
        return int(result.rowcount or 0)

    async def _cancel_expired_verification_orders(self, *, now: datetime) -> int:
        requests = (
            await self.db.scalars(
                select(Request).where(
                    Request.status == RequestStatus.verification_pending,
                    Request.verification_expires_at.is_not(None),
                    Request.verification_expires_at < now,
                )
            )
        ).all()

        cancelled = 0
        for request_row in requests:
            request_row.status = RequestStatus.cancelled
            request_row.admin_comment = "Истек срок подтверждения телефона"
            if request_row.points_spent and request_row.points_spent > 0:
                await self.points_service.refund_reserved_points_for_request(
                    user_id=request_row.user_id,
                    request_id=request_row.id,
                    admin_id=None,
                    source="order_verification_timeout",
                    comment="Автовозврат при истечении подтверждения СБП",
                    commit=False,
                )
            cancelled += 1

        return cancelled
