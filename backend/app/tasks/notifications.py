import asyncio
import logging
import uuid
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

from app.core.database import SessionLocal
from app.models.enums import SystemLogLevel
from app.models.system_log import SystemLog
from app.services.notifications import NotificationService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_BATCH_RETRIES = 3
SOFT_TIME_LIMIT_SECONDS = 5 * 60
HARD_TIME_LIMIT_SECONDS = 6 * 60


@celery_app.task(
    bind=True,
    name="app.tasks.notifications.send_notification_batch_task",
    autoretry_for=(DBAPIError, OperationalError, ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": MAX_BATCH_RETRIES},
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=SOFT_TIME_LIMIT_SECONDS,
    time_limit=HARD_TIME_LIMIT_SECONDS,
)
def send_notification_batch_task(self, *, items: list[dict[str, Any]]) -> dict[str, Any]:
    task_id = self.request.id
    logger.info(
        "send_notification_batch_task started: task_id=%s items=%s",
        task_id,
        len(items),
    )
    try:
        result = asyncio.run(_run_send_notification_batch(items))
        logger.info(
            "send_notification_batch_task finished: task_id=%s sent=%s skipped=%s",
            task_id,
            result.get("sent_count"),
            result.get("skipped_count"),
        )
        return result
    except SoftTimeLimitExceeded:
        logger.exception("send_notification_batch_task soft time limit: task_id=%s", task_id)
        raise
    except (SQLAlchemyError, ConnectionError, TimeoutError, OSError):
        logger.exception(
            "send_notification_batch_task transient error: task_id=%s retry=%s/%s",
            task_id,
            self.request.retries + 1,
            MAX_BATCH_RETRIES,
        )
        raise


async def _run_send_notification_batch(items: list[dict[str, Any]]) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        user_id_raw = item.get("user_id")
        if user_id_raw is None:
            continue
        normalized.append(
            {
                **item,
                "user_id": uuid.UUID(str(user_id_raw)),
            }
        )

    async with SessionLocal() as db:
        result = await NotificationService(db).send_batch(items=normalized, commit=True)
        if result["sent_count"] > 0:
            db.add(
                SystemLog(
                    level=SystemLogLevel.INFO,
                    source="celery",
                    message="Пакетная рассылка уведомлений",
                    details=str(result),
                )
            )
            await db.commit()
        return result
