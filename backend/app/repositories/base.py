"""Generic repository: common CRUD + pagination over a SQLAlchemy model.
Domain repositories subclass this and add their own filtered queries."""

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, id_: int) -> ModelT | None:
        return self._session.get(self.model, id_)

    def add(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        self._session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        self._session.delete(instance)
        self._session.flush()

    def paginate(
        self, stmt: Select[tuple[ModelT]], *, limit: int, offset: int
    ) -> tuple[Sequence[ModelT], int]:
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = self._session.scalars(stmt.limit(limit).offset(offset)).all()
        return items, total
