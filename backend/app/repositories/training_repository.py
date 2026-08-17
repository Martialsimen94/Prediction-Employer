"""Data access for the training catalog and per-employee enrollments."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.training import EmployeeTraining, Training
from app.repositories.base import BaseRepository


class TrainingRepository(BaseRepository[Training]):
    model = Training

    def get_by_name(self, name: str) -> Training | None:
        return self._session.scalar(select(Training).where(Training.name == name))

    def search(
        self, *, query: str | None, limit: int, offset: int
    ) -> tuple[Sequence[Training], int]:
        stmt = select(Training)
        if query:
            stmt = stmt.where(Training.name.ilike(f"%{query}%"))
        stmt = stmt.order_by(Training.name)
        return self.paginate(stmt, limit=limit, offset=offset)


class EmployeeTrainingRepository(BaseRepository[EmployeeTraining]):
    model = EmployeeTraining

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[EmployeeTraining], int]:
        stmt = (
            select(EmployeeTraining)
            .where(EmployeeTraining.employee_id == employee_id)
            .order_by(EmployeeTraining.start_date.desc())
        )
        return self.paginate(stmt, limit=limit, offset=offset)
