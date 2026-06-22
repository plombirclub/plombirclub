import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.core.files import save_task_cover_image
from app.models.enums import TaskType, UserRole
from app.services.tasks import TasksService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    period_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    task_type: TaskType = TaskType.participation_conditions
    distributor_ids: list[uuid.UUID] = Field(min_length=1)
    cover_image_path: str | None = None


@router.get("")
async def list_tasks(
    period_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    task_type: TaskType = Query(default=TaskType.participation_conditions),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = TasksService(db)
    try:
        if auth.user.role == UserRole.admin:
            data = await service.list_tasks_admin(
                period_month=period_month,
                task_type=task_type,
                page=page,
                limit=limit,
            )
        else:
            data = await service.list_tasks_for_user(
                user=auth.user,
                period_month=period_month,
                task_type=task_type,
                page=page,
                limit=limit,
            )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.get("/current")
async def get_current_task(
    period_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    task_type: TaskType = Query(default=TaskType.participation_conditions),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = TasksService(db)
    try:
        data = await service.get_current_task(
            user=auth.user,
            period_month=period_month,
            task_type=task_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.get("/{task_id}")
async def get_task(
    task_id: uuid.UUID,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = TasksService(db)
    try:
        data = await service.get_task_for_user(user=auth.user, task_id=task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.post("/create")
async def create_task(
    payload: TaskCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = TasksService(db)
    try:
        data = await service.create_and_publish_task(
            admin=auth.user,
            title=payload.title,
            content=payload.content,
            period_month=payload.period_month,
            task_type=payload.task_type,
            distributor_ids=payload.distributor_ids,
            cover_image_path=payload.cover_image_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.post("/create-with-cover")
async def create_task_with_cover(
    title: str = Form(...),
    content: str = Form(...),
    period_month: str = Form(..., pattern=r"^\d{4}-\d{2}$"),
    task_type: TaskType = Form(default=TaskType.participation_conditions),
    distributor_ids: list[str] = Form(...),
    cover_image: UploadFile | None = File(default=None),
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    cover_image_path: str | None = None
    if cover_image is not None and cover_image.filename:
        cover_image_path = await save_task_cover_image(upload=cover_image)

    parsed_ids = [uuid.UUID(item) for item in distributor_ids]

    service = TasksService(db)
    try:
        data = await service.create_and_publish_task(
            admin=auth.user,
            title=title,
            content=content,
            period_month=period_month,
            task_type=task_type,
            distributor_ids=parsed_ids,
            cover_image_path=cover_image_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.post("/{task_id}/accept")
async def accept_task(
    task_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    service = TasksService(db)
    try:
        data = await service.accept_task(
            user=auth.user,
            task_id=task_id,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}
