import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.services.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationReadRequest(BaseModel):
    notification_ids: list[uuid.UUID] | None = None
    mark_all: bool = False


class NotificationTemplateUpdateRequest(BaseModel):
    template_text: str = Field(min_length=1)


@router.get("/")
async def list_notifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = NotificationService(db)
    data = await service.list_for_user(
        user_id=auth.user.id,
        page=page,
        limit=limit,
        unread_only=unread_only,
    )
    return {"success": True, "data": data}


@router.post("/read")
async def mark_notifications_read(
    payload: NotificationReadRequest,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = NotificationService(db)
    try:
        data = await service.mark_read(
            user_id=auth.user.id,
            notification_ids=payload.notification_ids,
            mark_all=payload.mark_all,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.get("/templates")
async def list_notification_templates(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = NotificationService(db)
    items = await service.list_templates()
    return {"success": True, "data": {"items": items}}


@router.put("/templates/{template_id}")
async def update_notification_template(
    template_id: uuid.UUID,
    payload: NotificationTemplateUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = NotificationService(db)
    try:
        data = await service.update_template(
            admin=auth.user,
            template_id=template_id,
            template_text=payload.template_text,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}
