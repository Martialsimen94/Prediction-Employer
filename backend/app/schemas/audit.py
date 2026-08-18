"""Audit log response schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AuditAction


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    table_name: str
    record_id: int
    action: AuditAction
    changed_by: int | None
    changed_at: datetime
    old_data: dict[str, object] | None
    new_data: dict[str, object] | None
