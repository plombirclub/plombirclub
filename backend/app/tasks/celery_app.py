from celery import Celery

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
)

celery_app.autodiscover_tasks(["app.tasks"])

from app.tasks import imports as _imports  # noqa: E402,F401
