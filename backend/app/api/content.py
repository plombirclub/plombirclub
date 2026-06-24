from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_auth
from app.core.database import get_db_session
from app.core.files import save_instruction_file, save_legal_file
from app.services.content import ContentService

router = APIRouter(prefix="/content", tags=["content"])


class ContentUpdateRequest(BaseModel):
    value: dict[str, Any] = Field(default_factory=dict)


@router.post("/instructions/upload")
async def upload_instruction_file(
    file: UploadFile = File(...),
    _: AuthContext = Depends(require_admin),
) -> dict[str, Any]:
    file_path, content_type = await save_instruction_file(upload=file)
    normalized = file_path.replace("\\", "/").lstrip("/")
    file_url = f"/uploads/{normalized}" if not normalized.startswith("uploads/") else f"/{normalized}"
    return {
        "success": True,
        "data": {
            "file_path": file_path,
            "content_type": content_type,
            "file_url": file_url,
        },
    }


@router.post("/legal/upload")
async def upload_legal_file(
    file: UploadFile = File(...),
    _: AuthContext = Depends(require_admin),
) -> dict[str, Any]:
    file_path, content_type = await save_legal_file(upload=file)
    normalized = file_path.replace("\\", "/").lstrip("/")
    file_url = f"/uploads/{normalized}" if not normalized.startswith("uploads/") else f"/{normalized}"
    return {
        "success": True,
        "data": {
            "file_path": file_path,
            "content_type": content_type,
            "file_url": file_url,
        },
    }


@router.get("/{slug}")
async def get_content(
    slug: str,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if slug != "legal_documents" and not auth.user.is_registration_complete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Завершите регистрацию для доступа к этому разделу",
        )
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
