from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "plombirclub",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    timezone="Europe/Moscow",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    beat_schedule={
        "check-points-deadlines": {
            "task": "app.tasks.scheduler.check_points_deadlines_task",
            "schedule": crontab(hour=0, minute=1),
        },
        "backup-postgres": {
            "task": "app.tasks.scheduler.backup_postgres_task",
            "schedule": crontab(hour=3, minute=0),
        },
        "run-product-parser": {
            "task": "app.tasks.scheduler.run_product_parser_task",
            "schedule": crontab(hour=4, minute=0, day_of_week=1),
        },
        "expire-verification-codes": {
            "task": "app.tasks.scheduler.expire_verification_codes_task",
            "schedule": crontab(minute="*/3"),
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])

from app.tasks import imports as _imports  # noqa: E402,F401
from app.tasks import notifications as _notifications  # noqa: E402,F401
from app.tasks import scheduler as _scheduler  # noqa: E402,F401
