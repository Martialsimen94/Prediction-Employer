"""Data access for retention recommendations."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.ml import Recommendation
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    def list_for_prediction(self, prediction_id: int) -> Sequence[Recommendation]:
        stmt = (
            select(Recommendation)
            .where(Recommendation.prediction_id == prediction_id)
            .order_by(Recommendation.id)
        )
        return self._session.scalars(stmt).all()
