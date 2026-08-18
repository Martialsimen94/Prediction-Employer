"""Data access for the audit log (populated by DB triggers, see db/sql/triggers.sql)."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def search(
        self, *, table_name: str | None, record_id: int | None, limit: int, offset: int
    ) -> tuple[Sequence[AuditLog], int]:
        stmt = select(AuditLog)
        if table_name is not None:
            stmt = stmt.where(AuditLog.table_name == table_name)
        if record_id is not None:
            stmt = stmt.where(AuditLog.record_id == record_id)
        stmt = stmt.order_by(AuditLog.changed_at.desc())
        return self.paginate(stmt, limit=limit, offset=offset)
