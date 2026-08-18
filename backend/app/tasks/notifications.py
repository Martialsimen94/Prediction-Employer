"""Async notification delivery.

Delivery itself is stubbed (logged) since no real email/push provider is
configured for this project — swap in a real client where noted. The task
is dispatched right after the notification row is flushed but before the
enclosing request's transaction commits, so it retries briefly if the row
isn't visible yet rather than assuming it always will be.
"""

import structlog
from celery import Task

from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.notification import Notification

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=5, default_retry_delay=2)  # type: ignore
def deliver_notification_task(self: Task, notification_id: int) -> None:
    with SessionLocal() as session:
        notification = session.get(Notification, notification_id)
        if notification is None:
            raise self.retry(exc=LookupError(f"Notification {notification_id} not visible yet"))

        # TODO: call a real email/push provider here.
        logger.info(
            "notification_delivered",
            notification_id=notification_id,
            user_id=notification.user_id,
            notification_type=notification.notification_type,
        )
