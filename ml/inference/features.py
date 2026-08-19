"""Reconstructs model-ready feature rows from `EmployeeFeatureSnapshot.features`
JSON blobs (Module 6's offline feature store). The JSON round-trip through
Postgres can hand numeric values back as `int` where the training pipeline
saw `float` (e.g. a snapshot value that happens to be a whole number), so
every numeric column is explicitly coerced back to float before it reaches
the pipeline's `ColumnTransformer` — which was fit on float64 columns and
whose `StandardScaler` step requires numeric input in the first place."""

from collections.abc import Sequence

import pandas as pd

from ml.etl.features import FEATURE_COLUMNS, NUMERIC_FEATURES


def feature_frame(snapshots: Sequence[dict[str, float | str]]) -> pd.DataFrame:
    df = pd.DataFrame(list(snapshots), columns=FEATURE_COLUMNS)
    df[NUMERIC_FEATURES] = df[NUMERIC_FEATURES].astype(float)
    return df


def feature_row(features: dict[str, float | str]) -> pd.Series:
    return feature_frame([features]).iloc[0]
