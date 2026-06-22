import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.models.enums import RequestStatus, VerificationMethod
from app.services.orders import OrdersService

router = APIRouter(prefix="/orders", tags=["orders"])


class CreateOrderRequest(BaseModel):
    prize_id: uuid.UUID
    amount_rub: Decimal = Field(gt=0)
    payout_phone: str | None = None


class ConfirmOrderCodeRequest(BaseModel):
    request_id: uuid.UUID
    method: VerificationMethod
    code: str | None = Field(default=None, min_length=6, max_length=6)


class UpdateOrderStatusRequest(BaseModel):
    status: RequestStatus
    admin_comment: str | None = Field(default=None, max_length=3000)


class FulfillOrderRequest(BaseModel):
    certificate_code: str | None = Field(default=None, max_length=255)
    certificate_url: str | None = Field(default=None, max_length=500)
    certificate_file_url: str | None = Field(default=None, max_length=500)
    payout_comment: str | None = Field(default=None, max_length=3000)
    payout_operation_id: str | None = Field(default=None, max_length=255)


@router.post("/")
async def create_order(
    payload: CreateOrderRequest,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = OrdersService(db)
    try:
        data = await service.create_order(
            user=auth.user,
            prize_id=payload.prize_id,
            amount_rub=payload.amount_rub,
            payout_phone=payload.payout_phone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/confirm-code")
async def confirm_order_code(
    payload: ConfirmOrderCodeRequest,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = OrdersService(db)
    try:
        data = await service.confirm_order_code(
            user=auth.user,
            request_id=payload.request_id,
            method=payload.method,
            code=payload.code,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/my")
async def my_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = OrdersService(db)
    data = await service.my_orders(user_id=auth.user.id, page=page, limit=limit)
    return {"success": True, "data": data}


@router.get("/all")
async def all_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = OrdersService(db)
    data = await service.all_orders(page=page, limit=limit, status_filter=status_filter)
    return {"success": True, "data": data}


@router.put("/{request_id}/status")
async def update_order_status(
    request_id: uuid.UUID,
    payload: UpdateOrderStatusRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = OrdersService(db)
    try:
        data = await service.update_status(
            admin=auth.user,
            request_id=request_id,
            new_status=payload.status,
            admin_comment=payload.admin_comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.put("/{request_id}/fulfill")
async def fulfill_order(
    request_id: uuid.UUID,
    payload: FulfillOrderRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = OrdersService(db)
    try:
        data = await service.fulfill_order(
            admin=auth.user,
            request_id=request_id,
            certificate_code=payload.certificate_code,
            certificate_url=payload.certificate_url,
            certificate_file_url=payload.certificate_file_url,
            payout_comment=payload.payout_comment,
            payout_operation_id=payload.payout_operation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}
