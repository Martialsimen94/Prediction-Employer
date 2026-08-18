"""Unit tests for training data loading."""

from pathlib import Path

import pandas as pd

from ml.training.data import load_training_frame


def test_load_training_frame_reaches_target_rows(
    sample_raw_df: pd.DataFrame, tmp_path: Path
) -> None:
    csv_path = tmp_path / "sample.csv"
    sample_raw_df.to_csv(csv_path, index=False)

    df = load_training_frame(csv_path, target_rows=20, random_state=0)

    assert len(df) == 20
    assert "is_outlier" not in df.columns
    assert "Attrition" in df.columns
