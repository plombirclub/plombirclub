from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.services.points import PaginationParams, PointsService

router = APIRouter(prefix="/points", tags=["points"])


class PointsConsentRequest(BaseModel):
    period_month: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}$",
    )


class PointsActivateRequest(BaseModel):
    period_month: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}$",
    )


@router.get("/balance")
async def get_balance(
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = PointsService(db)
    balance = await service.get_balance(user_id=auth.user.id)
    return {
        "success": True,
        "data": {
            **balance,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/history")
async def get_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = PointsService(db)
    history = await service.get_history(
        user_id=auth.user.id,
        pagination=PaginationParams(
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )
    return {"success": True, "data": history}


@router.get("/overview")
async def get_points_overview(
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = PointsService(db)
    data = await service.get_overview(user_id=auth.user.id)
    return {"success": True, "data": data}


@router.post("/consent")
async def give_participation_consent(
    request: Request,
    payload: PointsConsentRequest | None = None,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = PointsService(db)
    try:
        result = await service.save_participation_consent(
            user=auth.user,
            period_month=payload.period_month if payload else None,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": result}


@router.post("/activate")
async def activate_points(
    request: Request,
    payload: PointsActivateRequest | None = None,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = PointsService(db)
    try:
        result = await service.activate_pending_points(
            user_id=auth.user.id,
            period_month=payload.period_month if payload else None,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": result}


@router.get("/pending-activation")
async def get_pending_activation(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="pending_amount"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    period_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = PointsService(db)
    data = await service.list_pending_activation(
        pagination=PaginationParams(
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
        period_month=period_month,
    )
    return {"success": True, "data": data}
