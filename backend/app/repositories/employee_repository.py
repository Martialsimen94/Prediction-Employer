"""Data access for employees."""

from collections.abc import Sequence

from sqlalchemy import or_, select

from app.models.employee import Employee
from app.models.enums import EmploymentStatus
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    model = Employee

    def get_by_email(self, email: str) -> Employee | None:
        return self._session.scalar(select(Employee).where(Employee.email == email))

    def get_by_employee_number(self, employee_number: str) -> Employee | None:
        return self._session.scalar(
            select(Employee).where(Employee.employee_number == employee_number)
        )

    def search(
        self,
        *,
        query: str | None,
        department_id: int | None,
        employment_status: EmploymentStatus | None,
        manager_id: int | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Employee], int]:
        stmt = select(Employee)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Employee.first_name.ilike(like),
                    Employee.last_name.ilike(like),
                    Employee.email.ilike(like),
                    Employee.employee_number.ilike(like),
                )
            )
        if department_id is not None:
            stmt = stmt.where(Employee.department_id == department_id)
        if employment_status is not None:
            stmt = stmt.where(Employee.employment_status == employment_status)
        if manager_id is not None:
            stmt = stmt.where(Employee.manager_id == manager_id)
        stmt = stmt.order_by(Employee.last_name, Employee.first_name)
        return self.paginate(stmt, limit=limit, offset=offset)
