import io
import re
import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import PointsLedgerStatus, PointsOperationType, RequestStatus, UserRole
from app.models.points_ledger import PointsLedger
from app.models.points_operations_log import PointsOperationsLog
from app.models.request import Request
from app.models.user import User
from app.services.points import PointsService

IMPORT_COMMENT_RE = re.compile(
    r"^Импорт продаж: (.+?), (.+?), (.+?)(?:\|кор:([\d.]+))?(?:\|дата:([\d-]+))?$"
)
IMPORT_SOURCE_RE = re.compile(r"^import_sales:[^:]+:(tp|sv)$")


def _normalize_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _parse_import_role(source: str) -> str | None:
    match = IMPORT_SOURCE_RE.match(source)
    return match.group(1).upper() if match else None


def _parse_import_comment(comment: str | None) -> dict[str, Any]:
    if not comment:
        return {
            "client_name": None,
            "client_address": None,
            "product_name": None,
            "boxes_count": None,
            "document_date": None,
        }
    match = IMPORT_COMMENT_RE.match(comment.strip())
    if not match:
        return {
            "client_name": None,
            "client_address": None,
            "product_name": comment,
            "boxes_count": None,
            "document_date": None,
        }
    boxes_raw = match.group(4)
    boxes_count: float | None = None
    if boxes_raw is not None:
        try:
            boxes_count = float(Decimal(boxes_raw))
        except Exception:
            boxes_count = None
    return {
        "client_name": match.group(1).strip() or None,
        "client_address": match.group(2).strip() or None,
        "product_name": match.group(3).strip() or None,
        "boxes_count": boxes_count,
        "document_date": match.group(5) or None,
    }


def _serialize_import_row(
    ledger: PointsLedger,
    comment: str | None,
) -> dict[str, Any]:
    parsed = _parse_import_comment(comment)
    row_date = parsed["document_date"] or (
        ledger.created_at.date().isoformat() if ledger.created_at else None
    )
    return {
        "id": str(ledger.id),
        "period_month": ledger.period_month,
        "amount": float(_normalize_decimal(ledger.amount)),
        "boxes_count": parsed["boxes_count"],
        "status": ledger.status.value,
        "role": _parse_import_role(ledger.source),
        "client_name": parsed["client_name"],
        "client_address": parsed["client_address"],
        "product_name": parsed["product_name"],
        "document_date": row_date,
        "created_at": ledger.created_at.isoformat() if ledger.created_at else None,
    }


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.points_service = PointsService(db)

    async def get_balance(self, *, user_id: uuid.UUID) -> dict[str, Any]:
        return await self.points_service.get_balance(user_id=user_id)

    async def _fetch_import_rows(
        self,
        *,
        user_id: uuid.UUID,
        period_month: str | None = None,
    ) -> list[dict[str, Any]]:
        conditions = [
            PointsLedger.user_id == user_id,
            PointsLedger.source.like("import_sales:%"),
        ]
        if period_month:
            conditions.append(PointsLedger.period_month == period_month)

        ledger_rows = (
            await self.db.scalars(
                select(PointsLedger)
                .where(*conditions)
                .order_by(PointsLedger.period_month.desc(), PointsLedger.created_at.desc())
            )
        ).all()
        if not ledger_rows:
            return []

        sources = {row.source for row in ledger_rows}
        log_rows = (
            await self.db.scalars(
                select(PointsOperationsLog)
                .where(
                    PointsOperationsLog.user_id == user_id,
                    PointsOperationsLog.source.in_(sources),
                    PointsOperationsLog.operation_type == PointsOperationType.import_,
                )
                .order_by(PointsOperationsLog.created_at.desc())
            )
        ).all()
        comments_by_source: dict[str, str | None] = {}
        for log_row in log_rows:
            if log_row.source not in comments_by_source:
                comments_by_source[log_row.source] = log_row.comment

        return [
            _serialize_import_row(row, comments_by_source.get(row.source))
            for row in ledger_rows
        ]

    async def get_my_analytics(
        self,
        *,
        user: User,
        period_month: str | None = None,
    ) -> dict[str, Any]:
        rows = await self._fetch_import_rows(user_id=user.id, period_month=period_month)

        total_points = Decimal("0.00")
        total_boxes = Decimal("0.00")
        by_period: dict[str, dict[str, Any]] = {}
        by_product: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

        for row in rows:
            amount = Decimal(str(row["amount"]))
            total_points += amount
            if row.get("boxes_count") is not None:
                total_boxes += Decimal(str(row["boxes_count"]))
            period = row["period_month"] or "unknown"
            period_bucket = by_period.setdefault(
                period,
                {
                    "period_month": period,
                    "points": Decimal("0.00"),
                    "boxes": Decimal("0.00"),
                    "rows_count": 0,
                },
            )
            period_bucket["points"] += amount
            if row.get("boxes_count") is not None:
                period_bucket["boxes"] += Decimal(str(row["boxes_count"]))
            period_bucket["rows_count"] += 1
            product_key = row["product_name"] or "Без названия"
            by_product[product_key] += amount

        return {
            "participant_code": user.participant_code,
            "participant_position": user.participant_position,
            "distributor_name": user.distributor.name if user.distributor else None,
            "summary": {
                "total_points": float(_normalize_decimal(total_points)),
                "total_boxes": float(_normalize_decimal(total_boxes)),
                "total_rows": len(rows),
            },
            "by_period": [
                {
                    "period_month": item["period_month"],
                    "points": float(_normalize_decimal(item["points"])),
                    "boxes": float(_normalize_decimal(item["boxes"])),
                    "rows_count": item["rows_count"],
                }
                for item in sorted(by_period.values(), key=lambda x: x["period_month"], reverse=True)
            ],
            "by_product": [
                {
                    "product_name": product_name,
                    "points": float(_normalize_decimal(points)),
                }
                for product_name, points in sorted(
                    by_product.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ],
        }

    async def get_my_raw(
        self,
        *,
        user_id: uuid.UUID,
        page: int,
        limit: int,
        period_month: str | None = None,
    ) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)
        all_rows = await self._fetch_import_rows(user_id=user_id, period_month=period_month)

        total_count = len(all_rows)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        return {
            "items": all_rows[offset : offset + limit],
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def export_my_analytics(
        self,
        *,
        user_id: uuid.UUID,
        period_month: str | None = None,
    ) -> bytes:
        rows = await self._fetch_import_rows(user_id=user_id, period_month=period_month)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "analytics"
        sheet.append(
            [
                "Период",
                "Дата",
                "Роль",
                "Клиент",
                "Адрес",
                "Товар",
                "Кол-во кор",
                "Баллы",
                "Статус",
            ]
        )
        for row in rows:
            sheet.append(
                [
                    row["period_month"],
                    row["document_date"],
                    row["role"],
                    row["client_name"],
                    row["client_address"],
                    row["product_name"],
                    row["boxes_count"],
                    row["amount"],
                    row["status"],
                ]
            )

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.read()

    async def get_dashboard(self) -> dict[str, Any]:
        users_total = await self.db.scalar(
            select(func.count(User.id)).where(User.role == UserRole.user)
        )
        users_active = await self.db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.user,
                User.is_active.is_(True),
            )
        )
        users_registered = await self.db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.user,
                User.is_registration_complete.is_(True),
            )
        )

        points_rows = (
            await self.db.execute(
                select(
                    PointsLedger.status,
                    func.coalesce(func.sum(PointsLedger.amount), 0).label("total"),
                ).group_by(PointsLedger.status)
            )
        ).all()
        points_by_status = {
            status.value: float(_normalize_decimal(total))
            for status, total in points_rows
        }

        orders_rows = (
            await self.db.execute(
                select(Request.status, func.count(Request.id)).group_by(Request.status)
            )
        ).all()
        orders_by_status = {status.value: int(count) for status, count in orders_rows}

        pending_activation = await self.db.scalar(
            select(func.count(PointsLedger.id)).where(
                PointsLedger.status == PointsLedgerStatus.pending
            )
        )

        return {
            "users": {
                "total": int(users_total or 0),
                "active": int(users_active or 0),
                "registration_complete": int(users_registered or 0),
            },
            "points_by_status": points_by_status,
            "orders_by_status": orders_by_status,
            "pending_activation_count": int(pending_activation or 0),
        }

    async def get_user_analytics(
        self,
        *,
        user_id: uuid.UUID,
        period_month: str | None = None,
    ) -> dict[str, Any]:
        user = await self.db.scalar(
            select(User)
            .options(selectinload(User.distributor))
            .where(User.id == user_id)
        )
        if user is None:
            raise LookupError("Пользователь не найден")
        if user.role != UserRole.user:
            raise ValueError("Аналитика доступна только для участников")

        analytics = await self.get_my_analytics(user=user, period_month=period_month)
        balance = await self.get_balance(user_id=user.id)
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "participant_code": user.participant_code,
                "participant_position": user.participant_position,
                "distributor_name": user.distributor.name if user.distributor else None,
            },
            "balance": balance,
            "analytics": analytics,
        }
