"""Business logic for the training catalog and per-employee enrollments."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.training import EmployeeTraining, Training
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.training_repository import EmployeeTrainingRepository, TrainingRepository


class TrainingService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = TrainingRepository(session)

    def list(self, *, query: str | None, limit: int, offset: int) -> tuple[Sequence[Training], int]:
        return self._repo.search(query=query, limit=limit, offset=offset)

    def get(self, training_id: int) -> Training:
        training = self._repo.get(training_id)
        if training is None:
            raise NotFoundError("Training", training_id)
        return training

    def create(self, **fields: Any) -> Training:
        if self._repo.get_by_name(fields["name"]) is not None:
            raise ConflictError(f"Training '{fields['name']}' already exists")
        return self._repo.add(Training(**fields))

    def update(self, training_id: int, **changes: Any) -> Training:
        training = self.get(training_id)
        for field, value in changes.items():
            setattr(training, field, value)
        self._session.flush()
        return training

    def delete(self, training_id: int) -> None:
        self._repo.delete(self.get(training_id))


class EmployeeTrainingService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = EmployeeTrainingRepository(session)
        self._employees = EmployeeRepository(session)
        self._trainings = TrainingRepository(session)

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[EmployeeTraining], int]:
        self._ensure_employee_exists(employee_id)
        return self._repo.list_for_employee(employee_id, limit=limit, offset=offset)

    def get(self, enrollment_id: int) -> EmployeeTraining:
        enrollment = self._repo.get(enrollment_id)
        if enrollment is None:
            raise NotFoundError("EmployeeTraining", enrollment_id)
        return enrollment

    def enroll(self, employee_id: int, **fields: Any) -> EmployeeTraining:
        self._ensure_employee_exists(employee_id)
        if self._trainings.get(fields["training_id"]) is None:
            raise NotFoundError("Training", fields["training_id"])
        enrollment = EmployeeTraining(employee_id=employee_id, **fields)
        return self._repo.add(enrollment)

    def update(self, enrollment_id: int, **changes: Any) -> EmployeeTraining:
        enrollment = self.get(enrollment_id)
        for field, value in changes.items():
            setattr(enrollment, field, value)
        self._session.flush()
        return enrollment

    def delete(self, enrollment_id: int) -> None:
        self._repo.delete(self.get(enrollment_id))

    def _ensure_employee_exists(self, employee_id: int) -> None:
        if self._employees.get(employee_id) is None:
            raise NotFoundError("Employee", employee_id)
