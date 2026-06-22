from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin_log import AdminLog
from app.models.system_log import SystemLog
from app.models.user_actions_log import UserActionsLog


class LogsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_admin_logs(self, *, page: int, limit: int) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)
        total_count = int((await self.db.scalar(select(func.count(AdminLog.id)))) or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        items = (
            await self.db.scalars(
                select(AdminLog)
                .options(selectinload(AdminLog.admin))
                .order_by(AdminLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        return {
            "items": [
                {
                    "id": str(item.id),
                    "admin_id": str(item.admin_id),
                    "admin_name": item.admin.full_name if item.admin else None,
                    "admin_email": item.admin.email if item.admin else None,
                    "action": item.action,
                    "entity_type": item.entity_type,
                    "entity_id": str(item.entity_id) if item.entity_id else None,
                    "old_value": item.old_value,
                    "new_value": item.new_value,
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

    async def list_system_logs(self, *, page: int, limit: int, source: str | None = None) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)
        conditions = []
        if source:
            conditions.append(SystemLog.source == source)

        count_query = select(func.count(SystemLog.id))
        if conditions:
            count_query = count_query.where(*conditions)
        total_count = int((await self.db.scalar(count_query)) or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        query = select(SystemLog).order_by(SystemLog.created_at.desc())
        if conditions:
            query = query.where(*conditions)

        items = (await self.db.scalars(query.offset(offset).limit(limit))).all()
        return {
            "items": [
                {
                    "id": str(item.id),
                    "level": item.level.value,
                    "source": item.source,
                    "message": item.message,
                    "details": item.details,
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

    async def list_user_actions_logs(self, *, page: int, limit: int) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)
        total_count = int((await self.db.scalar(select(func.count(UserActionsLog.id)))) or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        items = (
            await self.db.scalars(
                select(UserActionsLog)
                .options(selectinload(UserActionsLog.user))
                .order_by(UserActionsLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        return {
            "items": [
                {
                    "id": str(item.id),
                    "user_id": str(item.user_id) if item.user_id else None,
                    "user_name": item.user.full_name if item.user else None,
                    "user_email": item.user.email if item.user else None,
                    "action": item.action,
                    "entity_type": item.entity_type,
                    "entity_id": str(item.entity_id) if item.entity_id else None,
                    "ip_address": item.ip_address,
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
