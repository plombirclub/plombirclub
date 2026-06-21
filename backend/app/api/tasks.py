import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.models.enums import TaskType
from app.services.tasks import TasksService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    period_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    task_type: TaskType = TaskType.participation_conditions
    distributor_ids: list[uuid.UUID] = Field(min_length=1)


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
