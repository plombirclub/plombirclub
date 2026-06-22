import asyncio
import base64
import binascii
import logging
import uuid

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

from app.core.database import SessionLocal
from app.models.user import User
from app.services.imports import ImportsService
from app.services.users import write_admin_log
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_IMPORT_RETRIES = 3
SOFT_TIME_LIMIT_SECONDS = 5 * 60
HARD_TIME_LIMIT_SECONDS = 6 * 60


@celery_app.task(
    bind=True,
    name="app.tasks.imports.import_users_task",
    autoretry_for=(DBAPIError, OperationalError, ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": MAX_IMPORT_RETRIES},
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=SOFT_TIME_LIMIT_SECONDS,
    time_limit=HARD_TIME_LIMIT_SECONDS,
)
def import_users_task(
    self,
    *,
    file_bytes_base64: str,
    import_file_name: str | None,
    admin_id: str | None,
) -> dict:
    task_id = self.request.id
    logger.info(
        "Celery import_users_task started: task_id=%s file=%s admin_id=%s",
        task_id,
        import_file_name,
        admin_id,
    )
    try:
        file_bytes = base64.b64decode(file_bytes_base64.encode("ascii"))
    except (ValueError, binascii.Error, UnicodeError):
        logger.exception(
            "Celery import_users_task invalid base64 payload: task_id=%s file=%s",
            task_id,
            import_file_name,
        )
        raise

    try:
        result = asyncio.run(
            _run_import_users_task(
                file_bytes=file_bytes,
                import_file_name=import_file_name,
                admin_id=admin_id,
            )
        )
        logger.info(
            "Celery import_users_task finished: task_id=%s file=%s processed=%s failed=%s",
            task_id,
            import_file_name,
            result.get("processed_count"),
            result.get("failed_count"),
        )
        return result
    except SoftTimeLimitExceeded:
        logger.exception(
            "Celery import_users_task soft time limit exceeded: task_id=%s file=%s",
            task_id,
            import_file_name,
        )
        raise
    except (SQLAlchemyError, ConnectionError, TimeoutError, OSError):
        logger.exception(
            "Celery import_users_task transient error: task_id=%s file=%s retry=%s/%s",
            task_id,
            import_file_name,
            self.request.retries + 1,
            MAX_IMPORT_RETRIES,
        )
        raise
    except Exception:
        logger.exception(
            "Celery import_users_task failed without retry: task_id=%s file=%s",
            task_id,
            import_file_name,
        )
        raise


async def _run_import_users_task(
    *,
    file_bytes: bytes,
    import_file_name: str | None,
    admin_id: str | None,
) -> dict:
    async with SessionLocal() as db:
        admin_uuid = uuid.UUID(admin_id) if admin_id else None
        result = await ImportsService(db).import_users_from_xlsx(file_bytes=file_bytes)

        if admin_uuid is not None:
            admin = await db.get(User, admin_uuid)
            if admin is not None:
                await write_admin_log(
                    db,
                    admin=admin,
                    action="import_users_xlsx_async",
                    entity_type="import",
                    old_value=None,
                    new_value={**result, "file_name": import_file_name},
                )
                await db.commit()

        return result


@celery_app.task(
    bind=True,
    name="app.tasks.imports.import_sales_task",
    autoretry_for=(DBAPIError, OperationalError, ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": MAX_IMPORT_RETRIES},
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=SOFT_TIME_LIMIT_SECONDS,
    time_limit=HARD_TIME_LIMIT_SECONDS,
)
def import_sales_task(
    self,
    *,
    file_bytes_base64: str,
    import_file_name: str | None,
    admin_id: str | None,
) -> dict:
    task_id = self.request.id
    logger.info(
        "Celery import_sales_task started: task_id=%s file=%s admin_id=%s",
        task_id,
        import_file_name,
        admin_id,
    )
    try:
        file_bytes = base64.b64decode(file_bytes_base64.encode("ascii"))
    except (ValueError, binascii.Error, UnicodeError):
        logger.exception(
            "Celery import_sales_task invalid base64 payload: task_id=%s file=%s",
            task_id,
            import_file_name,
        )
        raise

    try:
        result = asyncio.run(
            _run_import_sales_task(
                file_bytes=file_bytes,
                import_file_name=import_file_name,
                admin_id=admin_id,
            )
        )
        logger.info(
            "Celery import_sales_task finished: task_id=%s file=%s processed=%s failed=%s",
            task_id,
            import_file_name,
            result.get("processed_count"),
            result.get("failed_count"),
        )
        return result
    except SoftTimeLimitExceeded:
        logger.exception(
            "Celery import_sales_task soft time limit exceeded: task_id=%s file=%s",
            task_id,
            import_file_name,
        )
        raise
    except (SQLAlchemyError, ConnectionError, TimeoutError, OSError):
        logger.exception(
            "Celery import_sales_task transient error: task_id=%s file=%s retry=%s/%s",
            task_id,
            import_file_name,
            self.request.retries + 1,
            MAX_IMPORT_RETRIES,
        )
        raise
    except Exception:
        logger.exception(
            "Celery import_sales_task failed without retry: task_id=%s file=%s",
            task_id,
            import_file_name,
        )
        raise


async def _run_import_sales_task(
    *,
    file_bytes: bytes,
    import_file_name: str | None,
    admin_id: str | None,
) -> dict:
    async with SessionLocal() as db:
        admin_uuid = uuid.UUID(admin_id) if admin_id else None
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
