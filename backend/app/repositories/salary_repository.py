"""Data access for salary history."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.salary import Salary
from app.repositories.base import BaseRepository


class SalaryRepository(BaseRepository[Salary]):
    model = Salary

    def get_current(self, employee_id: int) -> Salary | None:
        return self._session.scalar(
            select(Salary).where(Salary.employee_id == employee_id, Salary.end_date.is_(None))
        )

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[Salary], int]:
        stmt = (
            select(Salary)
            .where(Salary.employee_id == employee_id)
            .order_by(Salary.effective_date.desc())
        )
        return self.paginate(stmt, limit=limit, offset=offset)
