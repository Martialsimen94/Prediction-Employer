"""Notification creation (called by other services on key events) and
per-user consultation."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.tasks.notifications import deliver_notification_task


class NotificationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = NotificationRepository(session)

    def list_for_user(
        self, user_id: int, *, unread_only: bool, limit: int, offset: int
    ) -> tuple[Sequence[Notification], int]:
        return self._repo.list_for_user(
            user_id, unread_only=unread_only, limit=limit, offset=offset
        )

    def get_for_user(self, notification_id: int, user_id: int) -> Notification:
        notification = self._repo.get(notification_id)
        if notification is None or notification.user_id != user_id:
            raise NotFoundError("Notification", notification_id)
        return notification

    def mark_read(self, notification_id: int, user_id: int) -> Notification:
        notification = self.get_for_user(notification_id, user_id)
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        self._session.flush()
        return notification

    def notify(
        self,
        *,
        user_id: int,
        title: str,
        body: str,
        notification_type: str,
        related_entity_type: str | None = None,
        related_entity_id: int | None = None,
    ) -> Notification:
        notification = self._repo.add(
            Notification(
                user_id=user_id,
                title=title,
                body=body,
                notification_type=notification_type,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
            )
        )
        deliver_notification_task.delay(notification.id)
        return notification
