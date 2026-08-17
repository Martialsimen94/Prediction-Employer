"""Business logic for department management."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.department import Department
from app.models.employee import Employee
from app.repositories.department_repository import DepartmentRepository


class DepartmentService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = DepartmentRepository(session)

    def list(
        self, *, query: str | None, limit: int, offset: int
    ) -> tuple[Sequence[Department], int]:
        return self._repo.search(query=query, limit=limit, offset=offset)

    def get(self, department_id: int) -> Department:
        department = self._repo.get(department_id)
        if department is None:
            raise NotFoundError("Department", department_id)
        return department

    def create(self, *, name: str, description: str | None, manager_id: int | None) -> Department:
        if self._repo.get_by_name(name) is not None:
            raise ConflictError(f"Department '{name}' already exists")
        self._validate_manager(manager_id)
        department = Department(name=name, description=description, manager_id=manager_id)
        return self._repo.add(department)

    def update(self, department_id: int, **changes: Any) -> Department:
        department = self.get(department_id)
        if (
            "name" in changes
            and changes["name"] != department.name
            and self._repo.get_by_name(changes["name"]) is not None
        ):
            raise ConflictError(f"Department '{changes['name']}' already exists")
        if "manager_id" in changes:
            self._validate_manager(changes["manager_id"])
        for field, value in changes.items():
            setattr(department, field, value)
        self._session.flush()
        return department

    def delete(self, department_id: int) -> None:
        self._repo.delete(self.get(department_id))

    def _validate_manager(self, manager_id: int | None) -> None:
        if manager_id is not None and self._session.get(Employee, manager_id) is None:
            raise NotFoundError("Employee", manager_id)
