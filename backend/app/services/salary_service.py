"""Business logic for salary history. Salaries are an append-only ledger:
creating a new one closes the previously open row rather than editing it."""

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import SalaryChangeReason
from app.models.salary import Salary
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.salary_repository import SalaryRepository


class SalaryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = SalaryRepository(session)
        self._employees = EmployeeRepository(session)

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[Salary], int]:
        self._ensure_employee_exists(employee_id)
        return self._repo.list_for_employee(employee_id, limit=limit, offset=offset)

    def get(self, salary_id: int) -> Salary:
        salary = self._repo.get(salary_id)
        if salary is None:
            raise NotFoundError("Salary", salary_id)
        return salary

    def create(
        self,
        employee_id: int,
        *,
        amount: Decimal,
        currency: str,
        effective_date: date,
        reason: SalaryChangeReason,
    ) -> Salary:
        self._ensure_employee_exists(employee_id)
        current = self._repo.get_current(employee_id)
        if current is not None:
            if effective_date <= current.effective_date:
                raise ValidationError(
                    "New salary effective_date must be after the current salary's effective_date"
                )
            current.end_date = effective_date - timedelta(days=1)

        salary = Salary(
            employee_id=employee_id,
            amount=amount,
            currency=currency,
            effective_date=effective_date,
            reason=reason,
        )
        return self._repo.add(salary)

    def _ensure_employee_exists(self, employee_id: int) -> None:
        if self._employees.get(employee_id) is None:
            raise NotFoundError("Employee", employee_id)
