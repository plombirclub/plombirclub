from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin
from app.core.database import get_db_session
from app.models.enums import ImportType
from app.services.reports import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])


class CrmLayoutColumn(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    visible: bool = True


class CrmLayoutUpdateRequest(BaseModel):
    layout: list[CrmLayoutColumn] = Field(min_length=1)


@router.get("/layout")
async def get_crm_layout(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ReportsService(db)
    layout = await service.get_crm_layout()
    return {"success": True, "data": {"layout": layout}}


@router.put("/layout")
async def update_crm_layout(
    payload: CrmLayoutUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ReportsService(db)
    layout = await service.save_crm_layout(
        admin=auth.user,
        layout=[item.model_dump() for item in payload.layout],
    )
    return {"success": True, "data": {"layout": layout}}


@router.get("/users")
async def get_users_report(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ReportsService(db)
    data = await service.get_users_report(
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {"success": True, "data": data}


@router.get("/users/download")
async def download_users_report(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    service = ReportsService(db)
    payload = await service.build_users_report_xlsx()
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="crm-users-report.xlsx"'},
    )


@router.get("/sync-errors")
async def get_sync_errors(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    import_type: ImportType | None = Query(default=None),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ReportsService(db)
    data = await service.get_sync_errors(
        page=page,
        limit=limit,
        import_type=import_type,
    )
    return {"success": True, "data": data}


@router.get("/sync-errors/download")
async def download_sync_errors(
    import_type: ImportType | None = Query(default=None),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    service = ReportsService(db)
    payload = await service.build_sync_errors_xlsx(import_type=import_type)
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="sync-errors.xlsx"'},
    )
