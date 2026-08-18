"""Unit tests for SHAP-based per-instance feature attribution."""

import pandas as pd
import pytest
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ml.etl.features import FEATURE_COLUMNS, build_feature_pipeline, split_features_and_target
from ml.explainability.shap_explainer import ShapExplainer


def _fitted_pipeline(
    sample_raw_df: pd.DataFrame, classifier: ClassifierMixin
) -> tuple[Pipeline, pd.DataFrame]:
    df = pd.concat([sample_raw_df] * 10, ignore_index=True)
    x, y = split_features_and_target(df)
    pipeline = Pipeline([("preprocess", build_feature_pipeline()), ("classifier", classifier)])
    pipeline.fit(x, y)
    return pipeline, x


def test_explain_reconstructs_predicted_probability_for_tree_model(
    sample_raw_df: pd.DataFrame,
) -> None:
    pipeline, x = _fitted_pipeline(
        sample_raw_df, RandomForestClassifier(n_estimators=20, random_state=0)
    )
    explainer = ShapExplainer(pipeline, background=x)
    row = x.iloc[[0]]

    [explanation] = explainer.explain(row)
    predicted = pipeline.predict_proba(row)[0, 1]

    assert explanation.total == pytest.approx(predicted, abs=1e-6)


def test_explain_reconstructs_predicted_probability_for_non_tree_model(
    sample_raw_df: pd.DataFrame,
) -> None:
    pipeline, x = _fitted_pipeline(sample_raw_df, LogisticRegression(max_iter=1000))
    background = x.iloc[:15]
    explainer = ShapExplainer(pipeline, background=background)
    row = x.iloc[[0]]

    [explanation] = explainer.explain(row)
    predicted = pipeline.predict_proba(row)[0, 1]

    assert explanation.total == pytest.approx(predicted, abs=1e-3)


def test_explain_aggregates_onehot_columns_onto_original_features(
    sample_raw_df: pd.DataFrame,
) -> None:
    pipeline, x = _fitted_pipeline(
        sample_raw_df, RandomForestClassifier(n_estimators=20, random_state=0)
    )
    explainer = ShapExplainer(pipeline, background=x)

    [explanation] = explainer.explain(x.iloc[[0]])

    assert set(explanation.contributions) == set(FEATURE_COLUMNS)


def test_explain_returns_one_explanation_per_row(sample_raw_df: pd.DataFrame) -> None:
    pipeline, x = _fitted_pipeline(
        sample_raw_df, RandomForestClassifier(n_estimators=20, random_state=0)
    )
    explainer = ShapExplainer(pipeline, background=x)

    explanations = explainer.explain(x.iloc[:3])

    assert len(explanations) == 3
