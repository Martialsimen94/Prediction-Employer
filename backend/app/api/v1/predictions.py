"""Attrition prediction endpoints, nested under an employee, plus
recommendation endpoints addressed directly by id (they're worked on
independently of the prediction that generated them)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.models.ml import AttritionPrediction
from app.schemas.common import Page
from app.schemas.prediction import (
    PredictionDetailRead,
    PredictionRead,
    RecommendationRead,
    RecommendationStatusUpdate,
)
from app.services.prediction_service import PredictionService

employee_predictions_router = APIRouter(
    prefix="/employees/{employee_id}/predictions", tags=["predictions"]
)
predictions_router = APIRouter(prefix="/predictions", tags=["predictions"])
recommendations_router = APIRouter(prefix="/recommendations", tags=["predictions"])


def _detail(service: PredictionService, prediction: AttritionPrediction) -> PredictionDetailRead:
    recommendations = service.list_recommendations(prediction.id)
    return PredictionDetailRead(
        **PredictionRead.model_validate(prediction).model_dump(),
        recommendations=[RecommendationRead.model_validate(r) for r in recommendations],
    )


@employee_predictions_router.post(
    "", response_model=PredictionDetailRead, status_code=status.HTTP_201_CREATED
)
def create_prediction(
    employee_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("predictions:write")),
) -> PredictionDetailRead:
    service = PredictionService(db)
    prediction = service.predict_for_employee(employee_id)
    detail = _detail(service, prediction)
    db.commit()
    return detail


@employee_predictions_router.get("", response_model=Page[PredictionRead])
def list_predictions(
    employee_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("predictions:read")),
) -> Page[PredictionRead]:
    items, total = PredictionService(db).list_for_employee(employee_id, limit=limit, offset=offset)
    return Page(
        items=[PredictionRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@predictions_router.get("/{prediction_id}", response_model=PredictionDetailRead)
def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("predictions:read")),
) -> PredictionDetailRead:
    service = PredictionService(db)
    prediction = service.get(prediction_id)
    return _detail(service, prediction)


@recommendations_router.patch("/{recommendation_id}", response_model=RecommendationRead)
def update_recommendation(
    recommendation_id: int,
    payload: RecommendationStatusUpdate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("predictions:write")),
) -> RecommendationRead:
    recommendation = PredictionService(db).update_recommendation_status(
        recommendation_id, payload.status
    )
    db.commit()
    return RecommendationRead.model_validate(recommendation)
