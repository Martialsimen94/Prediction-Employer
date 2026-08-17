"""Business logic for performance reviews."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.performance_review import PerformanceReview
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.performance_review_repository import PerformanceReviewRepository


class PerformanceReviewService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PerformanceReviewRepository(session)
        self._employees = EmployeeRepository(session)

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[PerformanceReview], int]:
        self._ensure_employee_exists(employee_id)
        return self._repo.list_for_employee(employee_id, limit=limit, offset=offset)

    def get(self, review_id: int) -> PerformanceReview:
        review = self._repo.get(review_id)
        if review is None:
            raise NotFoundError("PerformanceReview", review_id)
        return review

    def create(self, employee_id: int, **fields: Any) -> PerformanceReview:
        self._ensure_employee_exists(employee_id)
        reviewer_id = fields.get("reviewer_id")
        if reviewer_id is not None and self._employees.get(reviewer_id) is None:
            raise NotFoundError("Employee", reviewer_id)
        review = PerformanceReview(employee_id=employee_id, **fields)
        return self._repo.add(review)

    def update(self, review_id: int, **changes: Any) -> PerformanceReview:
        review = self.get(review_id)
        for field, value in changes.items():
            setattr(review, field, value)
        self._session.flush()
        return review

    def _ensure_employee_exists(self, employee_id: int) -> None:
        if self._employees.get(employee_id) is None:
            raise NotFoundError("Employee", employee_id)
