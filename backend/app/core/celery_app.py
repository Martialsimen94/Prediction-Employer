"""Celery application: Redis as both broker and result backend."""

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery("retention_platform", broker=_settings.redis_dsn, backend=_settings.redis_dsn)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=("app.tasks.notifications",),
)
