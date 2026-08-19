"""Tests for the automated retraining policy: `should_retrain`'s threshold
logic (pure), and `retrain_and_promote`'s promote-only-if-better guard,
against an isolated temp MLflow tracking store (never the shared dev
mlruns.db — see ml/tests/test_training_pipeline_integration.py)."""

from pathlib import Path
from unittest.mock import patch

import mlflow
import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.models.enums import ModelStage
from app.models.ml import DataDriftReport, MLModelRegistry
from ml.monitoring.retrain import retrain_and_promote, should_retrain
from ml.training.evaluate import EvaluationResult
from ml.training.mlflow_utils import REGISTERED_MODEL_NAME
from ml.training.train import TrainedModel


def _report(*, drift_detected: bool) -> DataDriftReport:
    return DataDriftReport(
        feature_name="OverTime",
        reference_period_start="2024-01-01",
        reference_period_end="2024-01-01",
        current_period_start="2024-03-01",
        current_period_end="2024-03-01",
        drift_score="0.5",
        drift_detected=drift_detected,
        method="psi",
        generated_at="2024-03-01T00:00:00+00:00",
    )


def test_should_retrain_requires_the_minimum_number_of_drifted_features() -> None:
    reports = [_report(drift_detected=True)] * 2 + [_report(drift_detected=False)] * 5
    assert not should_retrain(reports, min_drifted_features=3)

    reports = [_report(drift_detected=True)] * 3 + [_report(drift_detected=False)] * 5
    assert should_retrain(reports, min_drifted_features=3)


@pytest.fixture
def small_training_csv(tmp_path: Path, sample_raw_df: pd.DataFrame) -> Path:
    df = pd.concat([sample_raw_df] * 20, ignore_index=True)
    df["EmployeeNumber"] = range(1, len(df) + 1)
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return path


def _fake_trained_model(roc_auc: float) -> TrainedModel:
    return TrainedModel(
        name="fake",
        run_id="fake-run",
        model_uri="runs:/fake-run/model",
        result=EvaluationResult(accuracy=0.5, precision=0.5, recall=0.5, f1=0.5, roc_auc=roc_auc),
        pipeline=None,  # type: ignore[arg-type]
    )


def test_retrain_and_promote_promotes_when_no_production_model_exists_yet(
    small_training_csv: Path, tmp_path: Path, db_session: Session
) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlruns_test.db'}"

    promoted = retrain_and_promote(
        db_session,
        target_rows=100,
        n_trials=2,
        tracking_uri=tracking_uri,
    )

    assert promoted is not None
    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    production = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, "production")
    assert production.run_id == promoted.run_id

    registry_entry = (
        db_session.query(MLModelRegistry).filter_by(mlflow_run_id=promoted.run_id).one()
    )
    assert registry_entry.stage == ModelStage.PRODUCTION
    assert registry_entry.promoted_at is not None


def test_retrain_and_promote_does_not_regress_a_better_production_model(
    small_training_csv: Path, tmp_path: Path, db_session: Session
) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlruns_test.db'}"

    # Seed a strong "production" baseline directly through the real
    # retraining path (deterministic given the fixed small dataset is
    # unnecessary here -- we only need *some* production baseline).
    first = retrain_and_promote(db_session, target_rows=100, n_trials=2, tracking_uri=tracking_uri)
    assert first is not None

    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    baseline = client.get_run(
        client.get_model_version_by_alias(REGISTERED_MODEL_NAME, "production").run_id
    ).data.metrics["roc_auc"]

    # A second "retrain" that's deliberately worse than the baseline must
    # not be promoted.
    with patch(
        "ml.monitoring.retrain.train_module.run",
        return_value=[_fake_trained_model(roc_auc=max(0.0, baseline - 0.5))],
    ):
        second = retrain_and_promote(
            db_session, target_rows=100, n_trials=2, tracking_uri=tracking_uri
        )

    assert second is None
    still_production = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, "production")
    assert still_production.run_id == first.run_id
