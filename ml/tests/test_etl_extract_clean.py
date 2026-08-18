"""Unit tests for the extract and clean ETL stages."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.etl.clean import drop_constant_columns, flag_outliers, handle_missing_values
from ml.etl.extract import extract


def test_extract_reads_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    pd.DataFrame({"Age": [30, 40], "Attrition": ["Yes", "No"]}).to_csv(csv_path, index=False)

    df = extract(csv_path)

    assert list(df.columns) == ["Age", "Attrition"]
    assert len(df) == 2


def test_extract_reads_excel(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "sample.xlsx"
    pd.DataFrame({"Age": [30, 40], "Attrition": ["Yes", "No"]}).to_excel(xlsx_path, index=False)

    df = extract(xlsx_path)

    assert list(df.columns) == ["Age", "Attrition"]
    assert len(df) == 2


def test_extract_rejects_unsupported_extension(tmp_path: Path) -> None:
    bad_path = tmp_path / "sample.json"
    bad_path.write_text("{}")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        extract(bad_path)


def test_drop_constant_columns_removes_known_noise_columns() -> None:
    df = pd.DataFrame(
        {
            "Age": [30],
            "EmployeeCount": [1],
            "StandardHours": [80],
            "Over18": ["Y"],
            "MonthlyRate": [12000],
        }
    )

    result = drop_constant_columns(df)

    assert list(result.columns) == ["Age"]


def test_handle_missing_values_imputes_numeric_median_and_categorical_mode() -> None:
    df = pd.DataFrame(
        {
            "MonthlyIncome": [1000.0, np.nan, 3000.0],
            "Department": ["Sales", "Sales", None],
        }
    )

    result = handle_missing_values(df)

    assert result["MonthlyIncome"].iloc[1] == 2000.0  # median of [1000, 3000]
    assert result["Department"].iloc[2] == "Sales"  # mode
    assert not result.isna().any().any()


def test_flag_outliers_marks_extreme_values() -> None:
    df = pd.DataFrame({"MonthlyIncome": [3000, 3100, 2900, 3050, 250000]})

    result = flag_outliers(df, columns=["MonthlyIncome"])

    assert result["is_outlier"].tolist() == [False, False, False, False, True]
