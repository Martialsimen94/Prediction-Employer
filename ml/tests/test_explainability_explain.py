"""Integration test for the explanation engine tying SHAP, LIME and the
recommendation engine together."""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

from ml.etl.features import build_feature_pipeline, split_features_and_target
from ml.explainability.explain import ExplanationEngine
from ml.explainability.recommendations import risk_level_from_score


def _fitted_pipeline_and_data(sample_raw_df: pd.DataFrame) -> tuple[Pipeline, pd.DataFrame]:
    df = pd.concat([sample_raw_df] * 10, ignore_index=True)
    x, y = split_features_and_target(df)
    pipeline = Pipeline(
        [
            ("preprocess", build_feature_pipeline()),
            ("classifier", RandomForestClassifier(n_estimators=20, random_state=0)),
        ]
    )
    pipeline.fit(x, y)
    return pipeline, x


def test_explain_produces_a_consistent_prediction_explanation(
    sample_raw_df: pd.DataFrame,
) -> None:
    pipeline, x = _fitted_pipeline_and_data(sample_raw_df)
    engine = ExplanationEngine(pipeline, background=x, top_n=5)

    explanation = engine.explain(x.iloc[0], max_recommendations=2)

    assert 0.0 <= explanation.risk_score <= 1.0
    assert explanation.risk_level == risk_level_from_score(explanation.risk_score)
    assert len(explanation.top_features) <= 5
    assert set(explanation.top_features).issubset(explanation.shap_values)
    assert explanation.lime_values
    assert len(explanation.recommendations) <= 2


def test_top_features_are_the_largest_magnitude_shap_contributions(
    sample_raw_df: pd.DataFrame,
) -> None:
    pipeline, x = _fitted_pipeline_and_data(sample_raw_df)
    engine = ExplanationEngine(pipeline, background=x, top_n=3)

    explanation = engine.explain(x.iloc[0])

    ranked_all = sorted(explanation.shap_values.values(), key=abs, reverse=True)
    assert sorted(explanation.top_features.values(), key=abs, reverse=True) == ranked_all[:3]
