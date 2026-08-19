"""Drift-report listing and manual drift-check triggering (Module 10)."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.ml import DataDriftReport
from app.repositories.drift_report_repository import DriftReportRepository
from app.tasks.monitoring import check_drift_and_retrain_task


class MonitoringService:
    def __init__(self, session: Session) -> None:
        self._repo = DriftReportRepository(session)

    def list_reports(
        self,
        *,
        feature_name: str | None,
        drift_detected: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[DataDriftReport], int]:
        return self._repo.search(
            feature_name=feature_name, drift_detected=drift_detected, limit=limit, offset=offset
        )

    def trigger_check(self) -> None:
        check_drift_and_retrain_task.delay()
