"""Notification response schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    notification_type: str
    is_read: bool
    read_at: datetime | None
    related_entity_type: str | None
    related_entity_id: int | None
    created_at: datetime
