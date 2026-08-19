"""Prediction and recommendation request/response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    RecommendationAction,
    RecommendationPriority,
    RecommendationStatus,
    RiskLevel,
)


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prediction_id: int
    action_type: RecommendationAction
    rationale: str
    priority: RecommendationPriority
    status: RecommendationStatus
    resolved_at: datetime | None


class RecommendationStatusUpdate(BaseModel):
    status: RecommendationStatus


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    model_registry_id: int | None
    risk_score: Decimal
    risk_level: RiskLevel
    predicted_at: datetime
    top_features: dict[str, float]
    shap_values: dict[str, float]


class PredictionDetailRead(PredictionRead):
    recommendations: list[RecommendationRead]
