"""Data access for absences."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.absence import Absence
from app.repositories.base import BaseRepository


class AbsenceRepository(BaseRepository[Absence]):
    model = Absence

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[Absence], int]:
        stmt = (
            select(Absence)
            .where(Absence.employee_id == employee_id)
            .order_by(Absence.start_date.desc())
        )
        return self.paginate(stmt, limit=limit, offset=offset)
