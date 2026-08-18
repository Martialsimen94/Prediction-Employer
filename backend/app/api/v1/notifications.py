"""Notification endpoints — always scoped to the authenticated user."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.auth import User
from app.schemas.common import Page
from app.schemas.notification import NotificationRead
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationRead])
def list_my_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[NotificationRead]:
    items, total = NotificationService(db).list_for_user(
        user.id, unread_only=unread_only, limit=limit, offset=offset
    )
    return Page(
        items=[NotificationRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{notification_id}", response_model=NotificationRead)
def get_my_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationRead:
    notification = NotificationService(db).get_for_user(notification_id, user.id)
    return NotificationRead.model_validate(notification)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationRead:
    notification = NotificationService(db).mark_read(notification_id, user.id)
    db.commit()
    return NotificationRead.model_validate(notification)
