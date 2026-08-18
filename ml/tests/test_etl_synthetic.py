"""Unit tests for bootstrap+jitter synthetic augmentation."""

import pandas as pd

from ml.etl.synthetic import augment


def test_augment_reaches_target_row_count(sample_raw_df: pd.DataFrame) -> None:
    result = augment(sample_raw_df, target_rows=20, random_state=1)
    assert len(result) == 20


def test_augment_keeps_all_original_rows(sample_raw_df: pd.DataFrame) -> None:
    result = augment(sample_raw_df, target_rows=20, random_state=1)
    original_numbers = set(sample_raw_df["EmployeeNumber"])
    assert original_numbers <= set(result["EmployeeNumber"])


def test_augment_assigns_unique_non_overlapping_employee_numbers(
    sample_raw_df: pd.DataFrame,
) -> None:
    result = augment(sample_raw_df, target_rows=20, random_state=1)
    assert result["EmployeeNumber"].is_unique


def test_augment_is_a_noop_when_target_not_larger_than_seed(sample_raw_df: pd.DataFrame) -> None:
    result = augment(sample_raw_df, target_rows=len(sample_raw_df), random_state=1)
    assert len(result) == len(sample_raw_df)
    assert set(result["EmployeeNumber"]) == set(sample_raw_df["EmployeeNumber"])


def test_augment_jitter_keeps_values_within_floor(sample_raw_df: pd.DataFrame) -> None:
    result = augment(sample_raw_df, target_rows=200, random_state=7)
    assert (result["Age"] >= 18).all()
    assert (result["MonthlyIncome"] >= 0).all()
    assert (result["YearsAtCompany"] >= 0).all()
