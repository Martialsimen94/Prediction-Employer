"""Data access for performance reviews."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.performance_review import PerformanceReview
from app.repositories.base import BaseRepository


class PerformanceReviewRepository(BaseRepository[PerformanceReview]):
    model = PerformanceReview

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[PerformanceReview], int]:
        stmt = (
            select(PerformanceReview)
            .where(PerformanceReview.employee_id == employee_id)
            .order_by(PerformanceReview.review_date.desc())
        )
        return self.paginate(stmt, limit=limit, offset=offset)
