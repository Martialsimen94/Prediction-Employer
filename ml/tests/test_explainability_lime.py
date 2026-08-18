"""Unit tests for LIME per-instance local-surrogate explanations."""

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ml.etl.features import FEATURE_COLUMNS, build_feature_pipeline, split_features_and_target
from ml.explainability.lime_explainer import LimeExplainer


def _fitted_pipeline_and_data(sample_raw_df: pd.DataFrame) -> tuple[Pipeline, pd.DataFrame]:
    df = pd.concat([sample_raw_df] * 10, ignore_index=True)
    x, y = split_features_and_target(df)
    pipeline = Pipeline(
        [
            ("preprocess", build_feature_pipeline()),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(x, y)
    return pipeline, x


def test_explain_returns_weights_for_known_features(sample_raw_df: pd.DataFrame) -> None:
    pipeline, x = _fitted_pipeline_and_data(sample_raw_df)
    explainer = LimeExplainer(pipeline, background=x)

    weights = explainer.explain(x.iloc[0], num_features=8)

    assert 0 < len(weights) <= 8
    assert set(weights).issubset(FEATURE_COLUMNS)
    assert all(isinstance(value, float) for value in weights.values())


def test_explain_num_features_caps_the_number_of_weights(sample_raw_df: pd.DataFrame) -> None:
    pipeline, x = _fitted_pipeline_and_data(sample_raw_df)
    explainer = LimeExplainer(pipeline, background=x)

    weights = explainer.explain(x.iloc[0], num_features=3)

    assert len(weights) <= 3
