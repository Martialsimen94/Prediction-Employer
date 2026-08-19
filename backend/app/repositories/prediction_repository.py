"""Data access for attrition predictions."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.ml import AttritionPrediction
from app.repositories.base import BaseRepository


class PredictionRepository(BaseRepository[AttritionPrediction]):
    model = AttritionPrediction

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[AttritionPrediction], int]:
        stmt = (
            select(AttritionPrediction)
            .where(AttritionPrediction.employee_id == employee_id)
            .order_by(AttritionPrediction.predicted_at.desc())
        )
        return self.paginate(stmt, limit=limit, offset=offset)
