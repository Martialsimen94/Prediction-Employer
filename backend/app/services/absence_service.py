"""Business logic for absences."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.absence import Absence
from app.repositories.absence_repository import AbsenceRepository
from app.repositories.employee_repository import EmployeeRepository


class AbsenceService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = AbsenceRepository(session)
        self._employees = EmployeeRepository(session)

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[Absence], int]:
        self._ensure_employee_exists(employee_id)
        return self._repo.list_for_employee(employee_id, limit=limit, offset=offset)

    def get(self, absence_id: int) -> Absence:
        absence = self._repo.get(absence_id)
        if absence is None:
            raise NotFoundError("Absence", absence_id)
        return absence

    def create(self, employee_id: int, **fields: Any) -> Absence:
        self._ensure_employee_exists(employee_id)
        absence = Absence(employee_id=employee_id, **fields)
        return self._repo.add(absence)

    def update(self, absence_id: int, **changes: Any) -> Absence:
        absence = self.get(absence_id)
        for field, value in changes.items():
            setattr(absence, field, value)
        self._session.flush()
        return absence

    def delete(self, absence_id: int) -> None:
        self._repo.delete(self.get(absence_id))

    def _ensure_employee_exists(self, employee_id: int) -> None:
        if self._employees.get(employee_id) is None:
            raise NotFoundError("Employee", employee_id)
