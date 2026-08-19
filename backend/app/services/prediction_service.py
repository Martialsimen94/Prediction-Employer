"""Business logic for attrition predictions: loads the current registered
model (Module 7) plus its explanation engine (Module 8), scores an employee
from their stored feature snapshot (Module 6's offline feature store), and
persists the resulting prediction and recommendations.

`ExplanationEngine` construction — fitting SHAP/LIME against a background
sample — is the dominant cost of scoring, so a fitted engine is cached at
process scope, keyed by the MLflow run id it was built from; a newly
promoted model (a different run id) invalidates the cache automatically."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import RecommendationStatus
from app.models.ml import AttritionPrediction, Recommendation
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from ml.explainability.explain import ExplanationEngine
from ml.inference.features import feature_frame, feature_row
from ml.inference.model_loader import get_or_create_registry_entry, load_pipeline

_ENGINE_CACHE: dict[str, ExplanationEngine] = {}

_RESOLVED_STATUSES = frozenset({RecommendationStatus.COMPLETED, RecommendationStatus.DISMISSED})


def reset_engine_cache() -> None:
    """Test-only escape hatch: clears the process-wide explanation-engine
    cache so a monkeypatched `load_pipeline` takes effect immediately
    instead of a previous test's cached engine leaking into this one."""
    _ENGINE_CACHE.clear()


class PredictionService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._employees = EmployeeRepository(session)
        self._snapshots = FeatureSnapshotRepository(session)
        self._predictions = PredictionRepository(session)
        self._recommendations = RecommendationRepository(session)

    def predict_for_employee(self, employee_id: int) -> AttritionPrediction:
        if self._employees.get(employee_id) is None:
            raise NotFoundError("Employee", employee_id)

        snapshot = self._snapshots.get_by_employee_id(employee_id)
        if snapshot is None:
            raise ValidationError(
                f"No feature snapshot for employee {employee_id}; "
                "run the ETL pipeline (ml.etl.pipeline) first."
            )

        engine, model_registry_id = self._engine_and_registry_id()
        explanation = engine.explain(feature_row(snapshot.features))

        prediction = self._predictions.add(
            AttritionPrediction(
                employee_id=employee_id,
                model_registry_id=model_registry_id,
                risk_score=Decimal(str(round(explanation.risk_score, 4))),
                risk_level=explanation.risk_level,
                predicted_at=datetime.now(UTC),
                top_features=explanation.top_features,
                shap_values=explanation.shap_values,
            )
        )

        for suggestion in explanation.recommendations:
            self._recommendations.add(
                Recommendation(
                    prediction_id=prediction.id,
                    action_type=suggestion.action_type,
                    rationale=suggestion.rationale,
                    priority=suggestion.priority,
                )
            )

        return prediction

    def list_for_employee(
        self, employee_id: int, *, limit: int, offset: int
    ) -> tuple[Sequence[AttritionPrediction], int]:
        if self._employees.get(employee_id) is None:
            raise NotFoundError("Employee", employee_id)
        return self._predictions.list_for_employee(employee_id, limit=limit, offset=offset)

    def get(self, prediction_id: int) -> AttritionPrediction:
        prediction = self._predictions.get(prediction_id)
        if prediction is None:
            raise NotFoundError("Prediction", prediction_id)
        return prediction

    def list_recommendations(self, prediction_id: int) -> Sequence[Recommendation]:
        return self._recommendations.list_for_prediction(prediction_id)

    def update_recommendation_status(
        self, recommendation_id: int, status: RecommendationStatus
    ) -> Recommendation:
        recommendation = self._recommendations.get(recommendation_id)
        if recommendation is None:
            raise NotFoundError("Recommendation", recommendation_id)
        recommendation.status = status
        recommendation.resolved_at = datetime.now(UTC) if status in _RESOLVED_STATUSES else None
        self._session.flush()
        return recommendation

    def _engine_and_registry_id(self) -> tuple[ExplanationEngine, int]:
        loaded = load_pipeline()
        registry_entry = get_or_create_registry_entry(self._session, loaded)

        engine = _ENGINE_CACHE.get(loaded.run_id)
        if engine is None:
            background = feature_frame([s.features for s in self._snapshots.sample()])
            engine = ExplanationEngine(loaded.pipeline, background)
            _ENGINE_CACHE[loaded.run_id] = engine

        return engine, registry_entry.id
