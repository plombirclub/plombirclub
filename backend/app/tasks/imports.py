import asyncio
import base64
import uuid

from app.core.database import SessionLocal
from app.models.user import User
from app.services.imports import ImportsService
from app.services.users import write_admin_log
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.imports.import_sales_task")
def import_sales_task(
    *,
    file_bytes_base64: str,
    import_file_name: str | None,
    admin_id: str | None,
) -> dict:
    return asyncio.run(
        _run_import_sales_task(
            file_bytes_base64=file_bytes_base64,
            import_file_name=import_file_name,
            admin_id=admin_id,
        )
    )


async def _run_import_sales_task(
    *,
    file_bytes_base64: str,
    import_file_name: str | None,
    admin_id: str | None,
) -> dict:
    async with SessionLocal() as db:
        admin_uuid = uuid.UUID(admin_id) if admin_id else None
        file_bytes = base64.b64decode(file_bytes_base64.encode("ascii"))
        result = await ImportsService(db).import_sales_from_xlsx(
            file_bytes=file_bytes,
            import_file_name=import_file_name,
            admin_id=admin_uuid,
        )

        if admin_uuid is not None:
            admin = await db.get(User, admin_uuid)
            if admin is not None:
                await write_admin_log(
                    db,
                    admin=admin,
                    action="import_sales_xlsx_async",
                    entity_type="import",
                    old_value=None,
                    new_value=result,
                )
                await db.commit()

        return result
