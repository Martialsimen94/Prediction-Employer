"""Celery application: Redis as both broker and result backend."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery("retention_platform", broker=_settings.redis_dsn, backend=_settings.redis_dsn)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=("app.tasks.notifications", "app.tasks.monitoring"),
    beat_schedule={
        # Module 10: a nightly drift check, auto-retraining (and promoting,
        # if it beats the currently-serving model) whenever enough features
        # have drifted since the reference period — see
        # app/tasks/monitoring.py.
        "check-drift-and-retrain-nightly": {
            "task": "app.tasks.monitoring.check_drift_and_retrain_task",
            "schedule": crontab(hour=2, minute=0),
        },
    },
)
