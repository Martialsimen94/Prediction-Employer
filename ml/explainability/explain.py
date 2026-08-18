"""Ties SHAP attribution, a LIME cross-check, and the recommendation
engine together into one per-employee explanation, shaped to match the
`attrition_predictions` / `recommendations` tables (see
backend/app/models/ml.py) so Module 9's inference API can persist it
directly."""

from dataclasses import dataclass

import pandas as pd
from sklearn.pipeline import Pipeline

from app.models.enums import RiskLevel
from ml.explainability.lime_explainer import LimeExplainer
from ml.explainability.recommendations import (
    RecommendationSuggestion,
    generate_recommendations,
    risk_level_from_score,
)
from ml.explainability.shap_explainer import ShapExplainer


@dataclass(frozen=True)
class PredictionExplanation:
    risk_score: float
    risk_level: RiskLevel
    shap_values: dict[str, float]
    top_features: dict[str, float]
    lime_values: dict[str, float]
    recommendations: list[RecommendationSuggestion]


class ExplanationEngine:
    """Fits both explainers once against a shared background sample (the
    dominant cost); explaining individual rows afterwards is cheap, so one
    engine instance is meant to be reused across many predictions."""

    def __init__(self, pipeline: Pipeline, background: pd.DataFrame, *, top_n: int = 10) -> None:
        self._pipeline = pipeline
        self._shap = ShapExplainer(pipeline, background)
        self._lime = LimeExplainer(pipeline, background)
        self._top_n = top_n

    def explain(self, x_row: pd.Series, *, max_recommendations: int = 3) -> PredictionExplanation:
        row_df = x_row.to_frame().T
        risk_score = float(self._pipeline.predict_proba(row_df)[0, 1])
        risk_level = risk_level_from_score(risk_score)

        shap_values = self._shap.explain(row_df)[0].contributions
        top_features = dict(
            sorted(shap_values.items(), key=lambda item: abs(item[1]), reverse=True)[: self._top_n]
        )
        lime_values = self._lime.explain(x_row)

        recommendations = generate_recommendations(
            top_features, x_row, risk_level, max_recommendations=max_recommendations
        )

        return PredictionExplanation(
            risk_score=risk_score,
            risk_level=risk_level,
            shap_values=shap_values,
            top_features=top_features,
            lime_values=lime_values,
            recommendations=recommendations,
        )
