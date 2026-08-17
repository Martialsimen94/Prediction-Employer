"""Business logic for employee management."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import EmploymentStatus
from app.repositories.employee_repository import EmployeeRepository


class EmployeeService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = EmployeeRepository(session)

    def list(
        self,
        *,
        query: str | None,
        department_id: int | None,
        employment_status: EmploymentStatus | None,
        manager_id: int | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Employee], int]:
        return self._repo.search(
            query=query,
            department_id=department_id,
            employment_status=employment_status,
            manager_id=manager_id,
            limit=limit,
            offset=offset,
        )

    def get(self, employee_id: int) -> Employee:
        employee = self._repo.get(employee_id)
        if employee is None:
            raise NotFoundError("Employee", employee_id)
        return employee

    def create(self, **fields: Any) -> Employee:
        if self._repo.get_by_email(fields["email"]) is not None:
            raise ConflictError(f"Email '{fields['email']}' already in use")
        if self._repo.get_by_employee_number(fields["employee_number"]) is not None:
            raise ConflictError(f"Employee number '{fields['employee_number']}' already in use")
        self._validate_department(fields.get("department_id"))
        self._validate_manager(fields.get("manager_id"), employee_id=None)
        employee = Employee(**fields)
        return self._repo.add(employee)

    def update(self, employee_id: int, **changes: Any) -> Employee:
        employee = self.get(employee_id)
        if (
            "email" in changes
            and changes["email"] != employee.email
            and self._repo.get_by_email(changes["email"]) is not None
        ):
            raise ConflictError(f"Email '{changes['email']}' already in use")
        if "department_id" in changes:
            self._validate_department(changes["department_id"])
        if "manager_id" in changes:
            self._validate_manager(changes["manager_id"], employee_id=employee_id)
        for field, value in changes.items():
            setattr(employee, field, value)
        self._session.flush()
        return employee

    def delete(self, employee_id: int) -> None:
        self._repo.delete(self.get(employee_id))

    def _validate_department(self, department_id: int | None) -> None:
        if department_id is not None and self._session.get(Department, department_id) is None:
            raise NotFoundError("Department", department_id)

    def _validate_manager(self, manager_id: int | None, *, employee_id: int | None) -> None:
        if manager_id is None:
            return
        if manager_id == employee_id:
            raise ValidationError("An employee cannot be their own manager")
        if self._session.get(Employee, manager_id) is None:
            raise NotFoundError("Employee", manager_id)
