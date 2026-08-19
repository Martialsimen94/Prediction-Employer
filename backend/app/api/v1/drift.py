"""Data drift report endpoints (Module 10). `predictions:read`/`write` are
reused rather than adding new permission rows: this is the same
ML-operations surface as triggering predictions (data_scientist can act on
it, hr/manager can only view it — see the seed migration's ROLE_PERMISSIONS)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.schemas.common import Page
from app.schemas.drift import DriftReportRead
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/drift-reports", tags=["monitoring"])


@router.get("", response_model=Page[DriftReportRead])
def list_drift_reports(
    feature_name: str | None = Query(default=None),
    drift_detected: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("predictions:read")),
) -> Page[DriftReportRead]:
    items, total = MonitoringService(db).list_reports(
        feature_name=feature_name, drift_detected=drift_detected, limit=limit, offset=offset
    )
    return Page(
        items=[DriftReportRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/check", status_code=status.HTTP_202_ACCEPTED)
def trigger_drift_check(
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("predictions:write")),
) -> dict[str, str]:
    """Enqueues an async drift-check-and-maybe-retrain run (Celery task,
    see backend/app/tasks/monitoring.py) rather than running it inline —
    a full retrain can take minutes."""
    MonitoringService(db).trigger_check()
    return {"status": "scheduled"}
