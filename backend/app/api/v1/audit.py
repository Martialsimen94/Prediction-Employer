"""Audit log endpoints — read-only, populated by DB triggers."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("", response_model=Page[AuditLogRead])
def list_audit_log(
    table_name: str | None = Query(default=None),
    record_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("audit:read")),
) -> Page[AuditLogRead]:
    items, total = AuditLogService(db).list(
        table_name=table_name, record_id=record_id, limit=limit, offset=offset
    )
    return Page(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
