"""Automated retraining policy: if enough features have drifted, retrain
every candidate model (ml.training.train, Module 7) and promote the new
run to the `production` MLflow alias only if it beats whichever model is
currently ahead — `production` if one has ever been promoted, `staging`
(i.e. the last training run, full stop) otherwise. This guards against a
bad retrain (e.g. a data-quality problem that also happens to look like
drift) ever silently regressing what's actually serving predictions."""

from collections.abc import Sequence
from datetime import UTC, datetime

import mlflow
from mlflow.exceptions import MlflowException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ModelStage
from app.models.ml import DataDriftReport, MLModelRegistry
from ml.training import train as train_module
from ml.training.mlflow_utils import REGISTERED_MODEL_NAME, configure_mlflow
from ml.training.train import TrainedModel

MIN_DRIFTED_FEATURES = 3


def should_retrain(
    reports: Sequence[DataDriftReport], *, min_drifted_features: int = MIN_DRIFTED_FEATURES
) -> bool:
    return sum(1 for report in reports if report.drift_detected) >= min_drifted_features


def _serving_roc_auc(client: mlflow.MlflowClient) -> float:
    for alias in ("production", "staging"):
        try:
            version = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, alias)
        except MlflowException:
            continue
        run = client.get_run(version.run_id)
        return float(run.data.metrics.get("roc_auc", 0.0))
    return 0.0


def _promote_registry_entry(
    session: Session, *, run_id: str, version: str, algorithm: str, metrics: dict[str, float]
) -> None:
    previous_production = session.scalar(
        select(MLModelRegistry).where(MLModelRegistry.stage == ModelStage.PRODUCTION)
    )
    if previous_production is not None:
        previous_production.stage = ModelStage.ARCHIVED

    entry = session.scalar(select(MLModelRegistry).where(MLModelRegistry.mlflow_run_id == run_id))
    if entry is None:
        entry = MLModelRegistry(
            model_name=REGISTERED_MODEL_NAME,
            version=version,
            algorithm=algorithm,
            mlflow_run_id=run_id,
            metrics=metrics,
            trained_at=datetime.now(UTC),
        )
        session.add(entry)
    entry.stage = ModelStage.PRODUCTION
    entry.promoted_at = datetime.now(UTC)
    session.flush()


def retrain_and_promote(
    session: Session,
    *,
    target_rows: int = 5000,
    n_trials: int = 12,
    tracking_uri: str | None = None,
) -> TrainedModel | None:
    """Runs the full training pipeline (which always registers its best
    result under the `staging` alias, per Module 7); promotes that result
    to `production` — and mirrors the promotion into `ml_model_registry` —
    only if it beats `_serving_roc_auc`. Returns the promoted run, or
    `None` if nothing was promoted."""
    configure_mlflow(tracking_uri)
    client = mlflow.MlflowClient()
    baseline_roc_auc = _serving_roc_auc(client)

    runs = train_module.run(target_rows=target_rows, n_trials=n_trials, tracking_uri=tracking_uri)
    best = max(runs, key=lambda r: r.result.roc_auc)

    if best.result.roc_auc <= baseline_roc_auc:
        return None

    new_version = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, "staging")
    client.set_registered_model_alias(
        name=REGISTERED_MODEL_NAME, alias="production", version=new_version.version
    )
    _promote_registry_entry(
        session,
        run_id=best.run_id,
        version=new_version.version,
        algorithm=best.name,
        metrics=best.result.as_mlflow_metrics(),
    )
    return best
