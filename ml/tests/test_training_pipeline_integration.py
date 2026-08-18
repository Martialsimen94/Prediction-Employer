"""End-to-end integration test for the training pipeline, using an isolated
temp MLflow tracking store (never the shared dev mlruns.db)."""

from pathlib import Path

import mlflow
import pandas as pd
import pytest

from ml.training.train import run


@pytest.fixture
def small_training_csv(tmp_path: Path, sample_raw_df: pd.DataFrame) -> Path:
    # Duplicated so every model has enough rows to fit within CV folds;
    # EmployeeNumber must stay unique for RawAttritionSchema to validate.
    df = pd.concat([sample_raw_df] * 20, ignore_index=True)
    df["EmployeeNumber"] = range(1, len(df) + 1)
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return path


def test_train_run_produces_a_result_per_model_and_registers_the_best(
    small_training_csv: Path, tmp_path: Path
) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlruns_test.db'}"

    runs = run(
        input_path=small_training_csv,
        target_rows=100,
        n_trials=2,
        tuning_cv_folds=2,
        final_cv_folds=2,
        tracking_uri=tracking_uri,
    )

    assert len(runs) == 6
    for trained in runs:
        assert 0.0 <= trained.result.roc_auc <= 1.0
        assert trained.run_id

    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    versions = client.search_model_versions("name='attrition-classifier'")
    assert len(versions) == 1
    assert client.get_model_version_by_alias("attrition-classifier", "staging") is not None
