import asyncio
import gzip
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import SystemLogLevel
from app.models.system_log import SystemLog
from app.services.parser import ParserService
from app.services.points import PointsService
from app.services.verification_cleanup import VerificationCleanupService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

SCHEDULER_SOFT_LIMIT = 10 * 60
SCHEDULER_HARD_LIMIT = 12 * 60
BACKUP_SOFT_LIMIT = 20 * 60
BACKUP_HARD_LIMIT = 25 * 60


async def _write_scheduler_log(
    *,
    message: str,
    level: SystemLogLevel = SystemLogLevel.INFO,
    details: str | None = None,
) -> None:
    async with SessionLocal() as db:
        db.add(
            SystemLog(
                level=level,
                source="scheduler",
                message=message,
                details=details,
            )
        )
        await db.commit()


@celery_app.task(
    bind=True,
    name="app.tasks.scheduler.check_points_deadlines_task",
    autoretry_for=(DBAPIError, OperationalError, ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=SCHEDULER_SOFT_LIMIT,
    time_limit=SCHEDULER_HARD_LIMIT,
)
def check_points_deadlines_task(self) -> dict[str, Any]:
    task_id = self.request.id
    logger.info("check_points_deadlines_task started: task_id=%s", task_id)
    try:
        result = asyncio.run(_run_check_points_deadlines())
        logger.info("check_points_deadlines_task finished: task_id=%s result=%s", task_id, result)
        return result
    except SoftTimeLimitExceeded:
        logger.exception("check_points_deadlines_task soft time limit: task_id=%s", task_id)
        raise
    except (SQLAlchemyError, ConnectionError, TimeoutError, OSError):
        logger.exception(
            "check_points_deadlines_task transient error: task_id=%s retry=%s/3",
            task_id,
            self.request.retries + 1,
        )
        raise


async def _run_check_points_deadlines() -> dict[str, Any]:
    async with SessionLocal() as db:
        result = await PointsService(db).expire_overdue_pending_points()
        if not result.get("skipped"):
            db.add(
                SystemLog(
                    level=SystemLogLevel.INFO,
                    source="scheduler",
                    message="Проверка дедлайнов активации баллов",
                    details=str(result),
                )
            )
            await db.commit()
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.scheduler.backup_postgres_task",
    autoretry_for=(DBAPIError, OperationalError, ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 2},
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=BACKUP_SOFT_LIMIT,
    time_limit=BACKUP_HARD_LIMIT,
)
def backup_postgres_task(self) -> dict[str, Any]:
    task_id = self.request.id
    logger.info("backup_postgres_task started: task_id=%s", task_id)
    try:
        result = _run_backup_postgres()
        asyncio.run(
            _write_scheduler_log(
                message="Резервное копирование PostgreSQL завершено",
                details=str(result),
            )
        )
        logger.info("backup_postgres_task finished: task_id=%s file=%s", task_id, result.get("file"))
        return result
    except SoftTimeLimitExceeded:
        logger.exception("backup_postgres_task soft time limit: task_id=%s", task_id)
        raise
    except (ConnectionError, TimeoutError, OSError, subprocess.SubprocessError):
        logger.exception(
            "backup_postgres_task error: task_id=%s retry=%s/2",
            task_id,
            self.request.retries + 1,
        )
        raise


def _run_backup_postgres() -> dict[str, Any]:
    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"plombirclub_{timestamp}.sql.gz"

    env = os.environ.copy()
    env["PGPASSWORD"] = settings.postgres_password
    dump = subprocess.run(
        [
            "pg_dump",
            "-h",
            settings.postgres_host,
            "-U",
            settings.postgres_user,
            "-d",
            settings.postgres_db,
        ],
        capture_output=True,
        check=False,
        env=env,
    )
    if dump.returncode != 0:
        raise RuntimeError(
            f"pg_dump failed (code {dump.returncode}): {dump.stderr.decode('utf-8', errors='ignore').strip()}"
        )

    with gzip.open(backup_file, "wb") as output:
        output.write(dump.stdout)

    backups = sorted(backup_dir.glob("plombirclub_*.sql.gz"), key=lambda path: path.stat().st_mtime, reverse=True)
    for old_file in backups[settings.backup_retain_count :]:
        old_file.unlink(missing_ok=True)

    return {"file": str(backup_file), "retained": min(len(backups), settings.backup_retain_count)}


@celery_app.task(
    bind=True,
    name="app.tasks.scheduler.run_product_parser_task",
    autoretry_for=(DBAPIError, OperationalError, ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 2},
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=SCHEDULER_SOFT_LIMIT,
    time_limit=SCHEDULER_HARD_LIMIT,
)
def run_product_parser_task(self) -> dict[str, Any]:
    task_id = self.request.id
    logger.info("run_product_parser_task started: task_id=%s", task_id)
    try:
        result = asyncio.run(_run_product_parser())
        logger.info("run_product_parser_task finished: task_id=%s", task_id)
        return result
    except SoftTimeLimitExceeded:
        logger.exception("run_product_parser_task soft time limit: task_id=%s", task_id)
        raise
    except (SQLAlchemyError, ConnectionError, TimeoutError, OSError, RuntimeError):
        logger.exception(
            "run_product_parser_task error: task_id=%s retry=%s/2",
            task_id,
            self.request.retries + 1,
        )
        raise


async def _run_product_parser() -> dict[str, Any]:
    async with SessionLocal() as db:
        return await ParserService(db).run_parser_scheduled()


@celery_app.task(
    bind=True,
    name="app.tasks.scheduler.expire_verification_codes_task",
    autoretry_for=(DBAPIError, OperationalError, ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=5 * 60,
    time_limit=6 * 60,
)
def expire_verification_codes_task(self) -> dict[str, Any]:
    try:
        return asyncio.run(_run_expire_verification_codes())
    except (SQLAlchemyError, ConnectionError, TimeoutError, OSError):
        logger.exception(
            "expire_verification_codes_task error: retry=%s/3",
            self.request.retries + 1,
        )
        raise


async def _run_expire_verification_codes() -> dict[str, Any]:
    async with SessionLocal() as db:
        return await VerificationCleanupService(db).expire_stale_records()
