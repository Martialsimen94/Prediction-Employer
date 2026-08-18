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


def test_augment_adds_lineage_id_tracing_back_to_the_real_seed_row(
    sample_raw_df: pd.DataFrame,
) -> None:
    """Every synthetic row must be traceable to the real seed row it was
    resampled from, so callers can group train/test splits and CV folds by
    lineage and avoid a synthetic row leaking its near-duplicate parent's
    label across the split (see ml/training/train.py)."""
    result = augment(sample_raw_df, target_rows=200, random_state=7)

    assert "lineage_id" in result.columns
    real_employee_numbers = set(sample_raw_df["EmployeeNumber"])
    assert set(result["lineage_id"]) == real_employee_numbers

    seed_rows = result[result["EmployeeNumber"].isin(real_employee_numbers)]
    assert (seed_rows["lineage_id"] == seed_rows["EmployeeNumber"]).all()

    synthetic_rows = result[~result["EmployeeNumber"].isin(real_employee_numbers)]
    assert synthetic_rows["lineage_id"].isin(real_employee_numbers).all()


def test_ordinal_jitter_stays_within_valid_range(sample_raw_df: pd.DataFrame) -> None:
    result = augment(sample_raw_df, target_rows=300, random_state=3)
    assert result["JobSatisfaction"].between(1, 4).all()
    assert result["Education"].between(1, 5).all()
    assert result["StockOptionLevel"].between(0, 3).all()
