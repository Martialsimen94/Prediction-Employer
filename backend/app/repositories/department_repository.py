"""Data access for departments."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.department import Department
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    def get_by_name(self, name: str) -> Department | None:
        return self._session.scalar(select(Department).where(Department.name == name))

    def search(
        self, *, query: str | None, limit: int, offset: int
    ) -> tuple[Sequence[Department], int]:
        stmt = select(Department)
        if query:
            stmt = stmt.where(Department.name.ilike(f"%{query}%"))
        stmt = stmt.order_by(Department.name)
        return self.paginate(stmt, limit=limit, offset=offset)
