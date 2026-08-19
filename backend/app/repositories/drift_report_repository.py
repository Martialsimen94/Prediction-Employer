"""Data access for data drift reports (Module 10)."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.ml import DataDriftReport
from app.repositories.base import BaseRepository


class DriftReportRepository(BaseRepository[DataDriftReport]):
    model = DataDriftReport

    def search(
        self,
        *,
        feature_name: str | None,
        drift_detected: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[DataDriftReport], int]:
        stmt = select(DataDriftReport)
        if feature_name is not None:
            stmt = stmt.where(DataDriftReport.feature_name == feature_name)
        if drift_detected is not None:
            stmt = stmt.where(DataDriftReport.drift_detected == drift_detected)
        stmt = stmt.order_by(DataDriftReport.generated_at.desc())
        return self.paginate(stmt, limit=limit, offset=offset)
