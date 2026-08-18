"""Unit tests for RawAttritionSchema validation."""

import pandas as pd
import pandera as pa
import pytest

from ml.etl.schema import RawAttritionSchema


def test_valid_dataframe_passes(sample_raw_df: pd.DataFrame) -> None:
    validated = RawAttritionSchema.validate(sample_raw_df, lazy=True)
    assert len(validated) == len(sample_raw_df)


def test_invalid_attrition_value_is_rejected(sample_raw_df: pd.DataFrame) -> None:
    bad_df = sample_raw_df.copy()
    bad_df.loc[0, "Attrition"] = "Maybe"

    with pytest.raises(pa.errors.SchemaErrors):
        RawAttritionSchema.validate(bad_df, lazy=True)


def test_out_of_range_satisfaction_score_is_rejected(sample_raw_df: pd.DataFrame) -> None:
    bad_df = sample_raw_df.copy()
    bad_df.loc[0, "EnvironmentSatisfaction"] = 9

    with pytest.raises(pa.errors.SchemaErrors):
        RawAttritionSchema.validate(bad_df, lazy=True)


def test_duplicate_employee_number_is_rejected(sample_raw_df: pd.DataFrame) -> None:
    bad_df = sample_raw_df.copy()
    bad_df.loc[1, "EmployeeNumber"] = bad_df.loc[0, "EmployeeNumber"]

    with pytest.raises(pa.errors.SchemaErrors):
        RawAttritionSchema.validate(bad_df, lazy=True)


def test_extra_columns_are_allowed(sample_raw_df: pd.DataFrame) -> None:
    df_with_extra = sample_raw_df.copy()
    df_with_extra["EmployeeCount"] = 1

    validated = RawAttritionSchema.validate(df_with_extra, lazy=True)
    assert "EmployeeCount" in validated.columns
