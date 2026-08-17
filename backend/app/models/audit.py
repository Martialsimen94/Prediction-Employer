"""Audit trail. Rows for sensitive tables are inserted automatically by DB triggers
(see db/sql/triggers.sql); application code may also write entries for business events."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, pg_enum
from app.models.enums import AuditAction


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_table_record", "table_name", "record_id"),
        Index("ix_audit_log_changed_at", "changed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        pg_enum(AuditAction, "audit_action"), nullable=False
    )
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    old_data: Mapped[dict[str, object] | None] = mapped_column(JSON)
    new_data: Mapped[dict[str, object] | None] = mapped_column(JSON)
