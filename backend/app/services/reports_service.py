"""Read-only reporting for the dashboards (Module 11), backed by the SQL
views/stored function in db/sql/ (Module 2)."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import RiskLevel
from app.repositories.department_repository import DepartmentRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.reports_repository import ReportsRepository


class ReportsService:
    def __init__(self, session: Session) -> None:
        self._repo = ReportsRepository(session)
        self._departments = DepartmentRepository(session)
        self._employees = EmployeeRepository(session)

    def department_kpis(self) -> Sequence[dict[str, Any]]:
        return self._repo.department_kpis()

    def risk_distribution(self, *, department_id: int | None) -> dict[str, int]:
        if department_id is not None and self._departments.get(department_id) is None:
            raise NotFoundError("Department", department_id)
        counts = self._repo.risk_distribution(department_id=department_id)
        return {level.value: counts.get(level.value, 0) for level in RiskLevel}

    def attrition_risk_summary(
        self,
        *,
        department_id: int | None,
        risk_level: RiskLevel | None,
        manager_id: int | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[dict[str, Any]], int]:
        if department_id is not None and self._departments.get(department_id) is None:
            raise NotFoundError("Department", department_id)
        if manager_id is not None and self._employees.get(manager_id) is None:
            raise NotFoundError("Employee", manager_id)
        return self._repo.attrition_risk_summary(
            department_id=department_id,
            risk_level=risk_level.value if risk_level is not None else None,
            manager_id=manager_id,
            limit=limit,
            offset=offset,
        )

    def employee_360(self, employee_id: int) -> dict[str, Any]:
        row = self._repo.employee_360(employee_id)
        if row is None:
            raise NotFoundError("Employee", employee_id)
        return row
