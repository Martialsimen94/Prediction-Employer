"""Data access for promotions."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.promotion import Promotion
from app.repositories.base import BaseRepository


class PromotionRepository(BaseRepository[Promotion]):
    model = Promotion

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[Promotion], int]:
        stmt = (
            select(Promotion)
            .where(Promotion.employee_id == employee_id)
            .order_by(Promotion.promotion_date.desc())
        )
        return self.paginate(stmt, limit=limit, offset=offset)
