import uuid
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.models.enums import ImportType
from app.services.analytics import AnalyticsService
from app.services.reports import ReportsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/my")
async def get_my_analytics(
    period_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AnalyticsService(db)
    data = await service.get_my_analytics(user=auth.user, period_month=period_month)
    return {"success": True, "data": data}


@router.get("/my-raw")
async def get_my_raw_analytics(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    period_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AnalyticsService(db)
    data = await service.get_my_raw(
        user_id=auth.user.id,
        page=page,
        limit=limit,
        period_month=period_month,
    )
    return {"success": True, "data": data}


@router.get("/balance")
async def get_analytics_balance(
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AnalyticsService(db)
    data = await service.get_balance(user_id=auth.user.id)
    return {"success": True, "data": data}


@router.get("/export")
async def export_my_analytics(
    period_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    service = AnalyticsService(db)
    payload = await service.export_my_analytics(
        user_id=auth.user.id,
        period_month=period_month,
    )
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="analytics.xlsx"'},
    )


@router.get("/dashboard")
async def get_analytics_dashboard(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AnalyticsService(db)
    data = await service.get_dashboard()
    return {"success": True, "data": data}


@router.get("/users/{user_id}")
async def get_user_analytics(
    user_id: uuid.UUID,
    period_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AnalyticsService(db)
    try:
        data = await service.get_user_analytics(user_id=user_id, period_month=period_month)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}
