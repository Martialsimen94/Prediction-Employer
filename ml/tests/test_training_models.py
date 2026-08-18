"""Unit tests for the model registry: every spec must build a fittable
estimator from its own suggested hyperparameters."""

import optuna
import pandas as pd
import pytest

from ml.etl.features import build_feature_pipeline, split_features_and_target
from ml.training.models import MODEL_SPECS, ModelSpec


@pytest.mark.parametrize("spec", MODEL_SPECS, ids=lambda s: s.name)
def test_model_spec_fits_and_predicts(spec: ModelSpec, sample_raw_df: pd.DataFrame) -> None:
    # Duplicate the tiny fixture so both classes have enough rows for a
    # StratifiedKFold-free single fit, and use a throwaway Optuna trial to
    # get valid sampled params for this spec.
    df = pd.concat([sample_raw_df] * 5, ignore_index=True)
    x, y = split_features_and_target(df)

    study = optuna.create_study(direction="maximize")
    trial = study.ask()
    params = spec.suggest_params(trial)

    pipeline = build_feature_pipeline()
    x_transformed = pipeline.fit_transform(x)
    estimator = spec.build(params)
    estimator.fit(x_transformed, y)
    predictions = estimator.predict(x_transformed)

    assert len(predictions) == len(y)
    assert set(predictions) <= {0, 1}


def test_model_specs_cover_all_required_algorithms() -> None:
    names = {spec.name for spec in MODEL_SPECS}
    assert names == {
        "logistic_regression",
        "random_forest",
        "xgboost",
        "lightgbm",
        "catboost",
        "neural_network",
    }
