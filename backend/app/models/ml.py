"""MLOps and prediction entities: model registry, predictions, recommendations, drift reports."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import (
    ModelStage,
    RecommendationAction,
    RecommendationPriority,
    RecommendationStatus,
    RiskLevel,
)

if TYPE_CHECKING:
    from app.models.employee import Employee


class MLModelRegistry(TimestampMixin, Base):
    __tablename__ = "ml_model_registry"
    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_ml_model_registry_name_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    mlflow_run_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    stage: Mapped[ModelStage] = mapped_column(
        pg_enum(ModelStage, "model_stage"),
        default=ModelStage.STAGING,
        nullable=False,
    )
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmployeeFeatureSnapshot(TimestampMixin, Base):
    """The raw model-input feature vector for one employee (see
    `ml.etl.features.FEATURE_COLUMNS`), refreshed whenever the ETL pipeline
    (Module 6) runs. Most of these columns have no other home in the
    relational schema -- salary/performance/absence/training data is
    normalized into its own domain tables, but fields like `JobLevel`,
    `OverTime` or `EnvironmentSatisfaction` only ever existed in the source
    HR dataset. This table is the offline feature store the inference API
    (Module 9) reads from to reconstruct exactly what the model was trained
    on, rather than trying to (lossily) re-derive it from operational data."""

    __tablename__ = "employee_feature_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), unique=True
    )
    features: Mapped[dict[str, float | str]] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    employee: Mapped["Employee"] = relationship("Employee")  # noqa: F821


class AttritionPrediction(TimestampMixin, Base):
    __tablename__ = "attrition_predictions"
    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 1", name="ck_attrition_predictions_score_range"
        ),
        Index("ix_attrition_predictions_employee_id", "employee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    model_registry_id: Mapped[int | None] = mapped_column(
        ForeignKey("ml_model_registry.id", ondelete="SET NULL")
    )
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(pg_enum(RiskLevel, "risk_level"), nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    top_features: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    shap_values: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)

    employee: Mapped["Employee"] = relationship("Employee")  # noqa: F821


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendations_prediction_id", "prediction_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("attrition_predictions.id", ondelete="CASCADE")
    )
    action_type: Mapped[RecommendationAction] = mapped_column(
        pg_enum(RecommendationAction, "recommendation_action"),
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[RecommendationPriority] = mapped_column(
        pg_enum(RecommendationPriority, "recommendation_priority"),
        nullable=False,
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        pg_enum(RecommendationStatus, "recommendation_status"),
        default=RecommendationStatus.PENDING,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    prediction: Mapped["AttritionPrediction"] = relationship("AttritionPrediction")


class DataDriftReport(TimestampMixin, Base):
    __tablename__ = "data_drift_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_name: Mapped[str] = mapped_column(String(150), nullable=False)
    reference_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    reference_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    current_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    current_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    drift_score: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    drift_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
