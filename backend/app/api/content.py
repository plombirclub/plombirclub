from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.services.content import ContentService

router = APIRouter(prefix="/content", tags=["content"])


class ContentUpdateRequest(BaseModel):
    value: dict[str, Any] = Field(default_factory=dict)


@router.get("/{slug}")
async def get_content(
    slug: str,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ContentService(db)
    try:
        data = await service.get_content(slug=slug, user=auth.user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.put("/{slug}")
async def update_content(
    slug: str,
    payload: ContentUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ContentService(db)
    try:
        data = await service.update_content(
            slug=slug,
            admin=auth.user,
            value=payload.value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}
