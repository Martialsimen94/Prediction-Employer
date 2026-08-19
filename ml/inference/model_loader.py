"""Loads the current attrition-classifier pipeline from the MLflow model
registry (Module 7's `ml.training.train`, which registers the best run
under a `staging` alias) and keeps the backend's `ml_model_registry` table
— the FK target `attrition_predictions.model_registry_id` points at — in
sync with whichever MLflow version is actually being served."""

from dataclasses import dataclass
from datetime import UTC, datetime

import mlflow
import mlflow.sklearn
from sklearn.pipeline import Pipeline
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ml import MLModelRegistry
from ml.training.mlflow_utils import REGISTERED_MODEL_NAME, configure_mlflow

DEFAULT_ALIAS = "staging"


@dataclass(frozen=True)
class LoadedModel:
    pipeline: Pipeline
    run_id: str
    version: str
    algorithm: str
    metrics: dict[str, float]


def load_pipeline(alias: str = DEFAULT_ALIAS) -> LoadedModel:
    """Raises `mlflow.exceptions.MlflowException` if no model carries
    `alias` yet — i.e. `ml.training.train` hasn't been run."""
    configure_mlflow()
    client = mlflow.MlflowClient()
    model_version = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, alias)
    run = client.get_run(model_version.run_id)
    pipeline = mlflow.sklearn.load_model(f"models:/{REGISTERED_MODEL_NAME}@{alias}")
    return LoadedModel(
        pipeline=pipeline,
        run_id=model_version.run_id,
        version=model_version.version,
        algorithm=run.data.params.get("model_type", "unknown"),
        metrics=dict(run.data.metrics),
    )


def get_or_create_registry_entry(session: Session, loaded: LoadedModel) -> MLModelRegistry:
    """The `ml_model_registry` table (Module 2's schema) mirrors MLflow's
    own registry for FK purposes; a row is created lazily here the first
    time inference serves a given `mlflow_run_id`, rather than requiring
    the training script to also write to Postgres."""
    entry = session.scalar(
        select(MLModelRegistry).where(MLModelRegistry.mlflow_run_id == loaded.run_id)
    )
    if entry is not None:
        return entry

    entry = MLModelRegistry(
        model_name=REGISTERED_MODEL_NAME,
        version=str(loaded.version),
        algorithm=loaded.algorithm,
        mlflow_run_id=loaded.run_id,
        metrics=loaded.metrics,
        trained_at=datetime.now(UTC),
    )
    session.add(entry)
    session.flush()
    return entry
