import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.core.files import save_material_file
from app.models.enums import MaterialContentType
from app.services.materials import MaterialsService

router = APIRouter(prefix="/materials", tags=["materials"])


class MaterialProgressRequest(BaseModel):
    action: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    video_percent: float | None = Field(default=None, ge=0, le=100)


@router.get("/")
async def list_materials(
    include_unpublished: bool = Query(default=False),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = MaterialsService(db)
    data = await service.list_materials(
        user=auth.user,
        include_unpublished=include_unpublished,
    )
    return {"success": True, "data": data}


@router.get("/{material_id}")
async def get_material(
    material_id: uuid.UUID,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = MaterialsService(db)
    try:
        data = await service.get_material(user=auth.user, material_id=material_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.post("/{material_id}/progress")
async def update_material_progress(
    material_id: uuid.UUID,
    payload: MaterialProgressRequest,
    request: Request,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = MaterialsService(db)
    try:
        data = await service.update_progress(
            user=auth.user,
            material_id=material_id,
            action=payload.action,
            page=payload.page,
            video_percent=payload.video_percent,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.post("/")
async def create_material(
    title: str = Form(...),
    content_type: MaterialContentType = Form(...),
    description: str | None = Form(default=None),
    total_pages: int | None = Form(default=None),
    sort_order: int = Form(default=0),
    is_published: bool = Form(default=False),
    file: UploadFile | None = File(default=None),
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    file_path: str | None = None
    if file is not None and file.filename:
        file_path = await save_material_file(upload=file)

    service = MaterialsService(db)
    try:
        data = await service.create_material(
            admin=auth.user,
            title=title,
            description=description,
            content_type=content_type,
            total_pages=total_pages,
            sort_order=sort_order,
            is_published=is_published,
            file_path=file_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.put("/{material_id}")
async def update_material(
    material_id: uuid.UUID,
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    content_type: MaterialContentType | None = Form(default=None),
    total_pages: int | None = Form(default=None),
    sort_order: int | None = Form(default=None),
    is_published: bool | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if content_type is not None:
        updates["content_type"] = content_type
    if total_pages is not None:
        updates["total_pages"] = total_pages
    if sort_order is not None:
        updates["sort_order"] = sort_order
    if is_published is not None:
        updates["is_published"] = is_published
    if file is not None and file.filename:
        updates["file_path"] = await save_material_file(upload=file)

    service = MaterialsService(db)
    try:
        data = await service.update_material(
            admin=auth.user,
            material_id=material_id,
            updates=updates,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.delete("/{material_id}")
async def hide_material(
    material_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = MaterialsService(db)
    try:
        data = await service.hide_material(admin=auth.user, material_id=material_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}
