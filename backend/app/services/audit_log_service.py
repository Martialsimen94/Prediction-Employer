"""Read-only access to the audit log."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditLogService:
    def __init__(self, session: Session) -> None:
        self._repo = AuditLogRepository(session)

    def list(
        self, *, table_name: str | None, record_id: int | None, limit: int, offset: int
    ) -> tuple[Sequence[AuditLog], int]:
        return self._repo.search(
            table_name=table_name, record_id=record_id, limit=limit, offset=offset
        )
