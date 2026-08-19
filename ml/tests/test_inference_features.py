"""Unit tests for reconstructing model-ready feature rows from
`EmployeeFeatureSnapshot.features` JSON blobs."""

from ml.etl.features import FEATURE_COLUMNS, NUMERIC_FEATURES
from ml.inference.features import feature_frame, feature_row
from ml.tests.conftest import _row


def _snapshot_features(**overrides: object) -> dict[str, float | str]:
    row = _row(1, **overrides)
    # Simulate the int-vs-float ambiguity a JSON round-trip through Postgres
    # can introduce for whole-number values.
    return {column: row[column] for column in FEATURE_COLUMNS}


def test_feature_row_coerces_numeric_columns_to_float() -> None:
    row = feature_row(_snapshot_features(JobLevel=2))

    assert list(row.index) == FEATURE_COLUMNS
    for column in NUMERIC_FEATURES:
        assert isinstance(row[column], float)
    assert row["JobLevel"] == 2.0
    assert row["Department"] == "Research & Development"


def test_feature_frame_stacks_multiple_snapshots_in_column_order() -> None:
    frame = feature_frame([_snapshot_features(JobLevel=1), _snapshot_features(JobLevel=5)])

    assert list(frame.columns) == FEATURE_COLUMNS
    assert list(frame["JobLevel"]) == [1.0, 5.0]
