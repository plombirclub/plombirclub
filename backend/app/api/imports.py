from io import BytesIO
import base64

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin
from app.core.database import get_db_session
from app.services.imports import ImportsService
from app.services.users import write_admin_log
from app.tasks.imports import import_sales_task

router = APIRouter(prefix="/import", tags=["import"])


@router.get("/template-users")
async def template_users(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    payload = await ImportsService(db).build_users_template()
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="template-users.xlsx"'},
    )


@router.post("/users")
async def import_users(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживается только формат .xlsx",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пустой",
        )

    service = ImportsService(db)
    try:
        result = await service.import_users_from_xlsx(file_bytes=file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await write_admin_log(
        db,
        admin=auth.user,
        action="import_users_xlsx",
        entity_type="import",
        old_value=None,
        new_value=result,
    )
    await db.commit()

    return {"success": True, "data": result}


@router.get("/template-sales")
async def template_sales(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    payload = await ImportsService(db).build_sales_template()
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="template-sales.xlsx"'},
    )


@router.post("/sales")
async def import_sales(
    file: UploadFile = File(...),
    use_celery: bool = Query(default=False),
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживается только формат .xlsx",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пустой",
        )

    if use_celery:
        task = import_sales_task.delay(
            file_bytes_base64=base64.b64encode(file_bytes).decode("ascii"),
            import_file_name=file.filename,
            admin_id=str(auth.user.id),
        )
        await write_admin_log(
            db,
            admin=auth.user,
            action="import_sales_xlsx_queued",
            entity_type="import",
            old_value=None,
            new_value={"task_id": task.id, "file_name": file.filename},
        )
        await db.commit()
        return {
            "success": True,
            "data": {
                "queued": True,
                "task_id": task.id,
                "message": "Импорт продаж поставлен в очередь Celery",
            },
        }

    service = ImportsService(db)
    try:
        result = await service.import_sales_from_xlsx(
            file_bytes=file_bytes,
            import_file_name=file.filename,
            admin_id=auth.user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await write_admin_log(
        db,
        admin=auth.user,
        action="import_sales_xlsx",
        entity_type="import",
        old_value=None,
        new_value=result,
    )
    await db.commit()

    return {"success": True, "data": result}
