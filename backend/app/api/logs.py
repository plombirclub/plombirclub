from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin
from app.core.database import get_db_session
from app.services.logs import LogsService

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/admin")
async def list_admin_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = LogsService(db)
    data = await service.list_admin_logs(page=page, limit=limit)
    return {"success": True, "data": data}


@router.get("/system")
async def list_system_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    source: str | None = Query(default=None),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = LogsService(db)
    data = await service.list_system_logs(page=page, limit=limit, source=source)
    return {"success": True, "data": data}


@router.get("/user-actions")
async def list_user_actions_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = LogsService(db)
    data = await service.list_user_actions_logs(page=page, limit=limit)
    return {"success": True, "data": data}
