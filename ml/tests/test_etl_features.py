"""Unit tests for the sklearn feature pipeline."""

import pandas as pd

from ml.etl.features import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_feature_pipeline,
    split_features_and_target,
)


def test_split_features_and_target(sample_raw_df: pd.DataFrame) -> None:
    features, target = split_features_and_target(sample_raw_df)

    assert list(features.columns) == NUMERIC_FEATURES + CATEGORICAL_FEATURES
    assert target.tolist() == [0, 0, 1, 0]  # matches the one Attrition="Yes" row


def test_feature_pipeline_fit_transform_shape(sample_raw_df: pd.DataFrame) -> None:
    features, _ = split_features_and_target(sample_raw_df)
    pipeline = build_feature_pipeline()

    transformed = pipeline.fit_transform(features)

    assert transformed.shape[0] == len(sample_raw_df)
    assert transformed.shape[1] > len(NUMERIC_FEATURES)  # one-hot expands categoricals
