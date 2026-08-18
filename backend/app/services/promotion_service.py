"""Business logic for promotions. Recording a promotion also applies its
new job title / department to the employee record; `promotions` is the
historical ledger of how that record got there."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.auth import User
from app.models.promotion import Promotion
from app.repositories.department_repository import DepartmentRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.promotion_repository import PromotionRepository
from app.services.notification_service import NotificationService


class PromotionService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PromotionRepository(session)
        self._employees = EmployeeRepository(session)
        self._departments = DepartmentRepository(session)
        self._notifications = NotificationService(session)

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[Promotion], int]:
        self._ensure_employee_exists(employee_id)
        return self._repo.list_for_employee(employee_id, limit=limit, offset=offset)

    def get(self, promotion_id: int) -> Promotion:
        promotion = self._repo.get(promotion_id)
        if promotion is None:
            raise NotFoundError("Promotion", promotion_id)
        return promotion

    def create(self, employee_id: int, **fields: Any) -> Promotion:
        employee = self._employees.get(employee_id)
        if employee is None:
            raise NotFoundError("Employee", employee_id)

        approved_by = fields.get("approved_by")
        if approved_by is not None and self._employees.get(approved_by) is None:
            raise NotFoundError("Employee", approved_by)

        new_department_id = fields.get("new_department_id")
        if new_department_id is not None and self._departments.get(new_department_id) is None:
            raise NotFoundError("Department", new_department_id)

        promotion = Promotion(employee_id=employee_id, **fields)
        self._repo.add(promotion)

        employee.job_title = fields["new_job_title"]
        if new_department_id is not None:
            employee.department_id = new_department_id
        self._session.flush()

        user = self._session.scalar(select(User).where(User.employee_id == employee_id))
        if user is not None:
            self._notifications.notify(
                user_id=user.id,
                title="You've been promoted!",
                body=f"Congratulations — your new title is {fields['new_job_title']}.",
                notification_type="promotion",
                related_entity_type="promotion",
                related_entity_id=promotion.id,
            )
        return promotion

    def _ensure_employee_exists(self, employee_id: int) -> None:
        if self._employees.get(employee_id) is None:
            raise NotFoundError("Employee", employee_id)
