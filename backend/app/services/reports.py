import io
import json
import uuid
from typing import Any

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin_setting import AdminSetting
from app.models.enums import ImportType, UserRole
from app.models.import_error_log import ImportErrorLog
from app.models.user import User

DEFAULT_CRM_LAYOUT: list[dict[str, Any]] = [
    {"id": "full_name", "label": "ФИО", "visible": True},
    {"id": "email", "label": "Email", "visible": True},
    {"id": "phone", "label": "Телефон", "visible": True},
    {"id": "inn", "label": "ИНН", "visible": False},
    {"id": "inn_verified_by_admin", "label": "ИНН подтвержден", "visible": True},
    {"id": "knd_1122035_number", "label": "Номер справки КНД 1122035", "visible": False},
    {"id": "is_self_employed", "label": "Самозанятый", "visible": True},
    {"id": "created_at", "label": "Дата регистрации", "visible": False},
]

CRM_FIELD_GETTERS: dict[str, Any] = {
    "full_name": lambda user: user.full_name,
    "email": lambda user: user.email,
    "phone": lambda user: user.phone,
    "inn": lambda user: user.inn,
    "inn_verified_by_admin": lambda user: user.inn_verified_by_admin,
    "knd_1122035_number": lambda user: user.knd_1122035_number,
    "is_self_employed": lambda user: user.is_self_employed,
    "created_at": lambda user: user.created_at.isoformat() if user.created_at else None,
    "participant_code": lambda user: user.participant_code,
    "participant_position": lambda user: user.participant_position,
    "distributor_name": lambda user: user.distributor.name if user.distributor else None,
    "is_active": lambda user: user.is_active,
    "is_registration_complete": lambda user: user.is_registration_complete,
}


def _normalize_layout(raw_layout: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not raw_layout:
        return DEFAULT_CRM_LAYOUT.copy()

    normalized: list[dict[str, Any]] = []
    for item in raw_layout:
        field_id = str(item.get("id", "")).strip()
        if not field_id or field_id not in CRM_FIELD_GETTERS:
            continue
        normalized.append(
            {
                "id": field_id,
                "label": str(item.get("label") or field_id).strip() or field_id,
                "visible": bool(item.get("visible", True)),
            }
        )
    return normalized or DEFAULT_CRM_LAYOUT.copy()


def _serialize_user_row(user: User, layout: list[dict[str, Any]]) -> dict[str, Any]:
    row: dict[str, Any] = {"id": str(user.id)}
    for column in layout:
        if not column["visible"]:
            continue
        getter = CRM_FIELD_GETTERS[column["id"]]
        row[column["id"]] = getter(user)
    return row


class ReportsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_crm_layout(self) -> list[dict[str, Any]]:
        stored = await self.db.scalar(
            select(AdminSetting)
            .where(AdminSetting.setting_key == "crm_report_layout")
            .order_by(AdminSetting.updated_at.desc())
            .limit(1)
        )
        if stored is None:
            return DEFAULT_CRM_LAYOUT.copy()
        raw_layout = stored.setting_value
        if isinstance(raw_layout, list):
            return _normalize_layout(raw_layout)
        return DEFAULT_CRM_LAYOUT.copy()

    async def save_crm_layout(
        self,
        *,
        admin: User,
        layout: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized_layout = _normalize_layout(layout)
        stored = await self.db.scalar(
            select(AdminSetting).where(
                AdminSetting.admin_id == admin.id,
                AdminSetting.setting_key == "crm_report_layout",
            )
        )
        if stored is None:
            stored = AdminSetting(
                admin_id=admin.id,
                setting_key="crm_report_layout",
                setting_value=normalized_layout,
            )
            self.db.add(stored)
        else:
            stored.setting_value = normalized_layout
        await self.db.commit()
        return normalized_layout

    async def get_users_report(
        self,
        *,
        page: int,
        limit: int,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)
        layout = await self.get_crm_layout()

        sortable = {
            "created_at": User.created_at,
            "email": User.email,
            "full_name": User.full_name,
        }
        sort_column = sortable.get(sort_by, User.created_at)
        sort_expr = sort_column.asc() if sort_order.lower() == "asc" else sort_column.desc()

        total_count = await self.db.scalar(
            select(func.count(User.id)).where(User.role == UserRole.user)
        )
        total_count = int(total_count or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        users = (
            await self.db.scalars(
                select(User)
                .options(selectinload(User.distributor))
                .where(User.role == UserRole.user)
                .order_by(sort_expr, User.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        visible_columns = [column for column in layout if column["visible"]]
        return {
            "columns": visible_columns,
            "items": [_serialize_user_row(user, layout) for user in users],
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def build_users_report_xlsx(self) -> bytes:
        layout = await self.get_crm_layout()
        visible_columns = [column for column in layout if column["visible"]]

        users = (
            await self.db.scalars(
                select(User)
                .options(selectinload(User.distributor))
                .where(User.role == UserRole.user)
                .order_by(User.created_at.desc(), User.id.desc())
            )
        ).all()

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "users"
        sheet.append([column["label"] for column in visible_columns])
        for user in users:
            row = _serialize_user_row(user, layout)
            sheet.append([row.get(column["id"]) for column in visible_columns])

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.read()

    async def get_sync_errors(
        self,
        *,
        page: int,
        limit: int,
        import_type: ImportType | None = None,
    ) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)

        conditions = []
        if import_type is not None:
            conditions.append(ImportErrorLog.import_type == import_type)

        total_count = await self.db.scalar(
            select(func.count(ImportErrorLog.id)).where(*conditions)
        )
        total_count = int(total_count or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        items = (
            await self.db.scalars(
                select(ImportErrorLog)
                .where(*conditions)
                .order_by(ImportErrorLog.created_at.desc(), ImportErrorLog.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        return {
            "items": [
                {
                    "id": str(item.id),
                    "import_type": item.import_type.value,
                    "row_number": item.row_number,
                    "error_message": item.error_message,
                    "raw_row_data": self._parse_raw_row(item.raw_row_data),
                    "created_at": item.created_at.isoformat() if item.created_at else None,
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

    async def build_sync_errors_xlsx(
        self,
        *,
        import_type: ImportType | None = None,
    ) -> bytes:
        conditions = []
        if import_type is not None:
            conditions.append(ImportErrorLog.import_type == import_type)

        items = (
            await self.db.scalars(
                select(ImportErrorLog)
                .where(*conditions)
                .order_by(ImportErrorLog.created_at.desc(), ImportErrorLog.id.desc())
            )
        ).all()

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "sync-errors"
        sheet.append(["Тип импорта", "Строка", "Ошибка", "Данные строки", "Дата"])
        for item in items:
            sheet.append(
                [
                    item.import_type.value,
                    item.row_number,
                    item.error_message,
                    json.dumps(self._parse_raw_row(item.raw_row_data), ensure_ascii=False),
                    item.created_at.isoformat() if item.created_at else None,
                ]
            )

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.read()

    def _parse_raw_row(self, raw_row_data: str | None) -> Any:
        if not raw_row_data:
            return None
        try:
            return json.loads(raw_row_data)
        except json.JSONDecodeError:
            return raw_row_data
