"""Unit tests for the domain-mapping transform stage."""

from decimal import Decimal

import pandas as pd

from ml.etl.features import FEATURE_COLUMNS
from ml.etl.transform import (
    EDUCATION_LEVELS,
    assign_managers,
    build_departments,
    department_managers,
    to_absence_records,
    to_employee_feature_records,
    to_employee_records,
    to_employee_training_records,
    to_performance_review_records,
    to_salary_records,
)


def test_build_departments_returns_unique_sorted_names(sample_raw_df: pd.DataFrame) -> None:
    departments = build_departments(sample_raw_df)
    assert list(departments["name"]) == ["Research & Development", "Sales"]


def test_assign_managers_picks_highest_job_level_per_department(
    sample_raw_df: pd.DataFrame,
) -> None:
    with_managers = assign_managers(sample_raw_df)

    # Employee 1 (JobLevel 4) manages R&D; employee 3 (JobLevel 3) manages Sales.
    assert (
        with_managers.loc[with_managers["EmployeeNumber"] == 2, "manager_employee_number"].iat[0]
        == 1
    )
    assert (
        with_managers.loc[with_managers["EmployeeNumber"] == 4, "manager_employee_number"].iat[0]
        == 3
    )
    # The top-of-department employees have no manager of their own.
    assert pd.isna(
        with_managers.loc[with_managers["EmployeeNumber"] == 1, "manager_employee_number"].iat[0]
    )


def test_department_managers_maps_name_to_top_employee(sample_raw_df: pd.DataFrame) -> None:
    with_managers = assign_managers(sample_raw_df)
    managers = department_managers(with_managers)

    assert managers == {"Research & Development": 1, "Sales": 3}


def test_to_employee_records_maps_core_fields(sample_raw_df: pd.DataFrame) -> None:
    with_managers = assign_managers(sample_raw_df)
    records = to_employee_records(with_managers, random_state=0)

    assert len(records) == 4
    assert set(records["employee_number"]) == {
        "EMP-000001",
        "EMP-000002",
        "EMP-000003",
        "EMP-000004",
    }
    active_row = records[records["source_employee_number"] == 1].iloc[0]
    assert active_row["employment_status"] == "active"
    assert active_row["termination_date"] is None
    assert active_row["education_level"] == EDUCATION_LEVELS[3]

    terminated_row = records[records["source_employee_number"] == 3].iloc[0]
    assert terminated_row["employment_status"] == "terminated"
    assert terminated_row["termination_date"] is not None


def test_termination_date_is_never_before_hire_date_even_with_short_tenure() -> None:
    """Regression test: a terminated employee whose (post-jitter) tenure is
    very short must not get a termination_date before their hire_date."""
    df = pd.DataFrame(
        [
            {
                "EmployeeNumber": 99,
                "Attrition": "Yes",
                "Age": 22,
                "YearsAtCompany": 0,
                "Department": "Sales",
                "JobRole": "Sales Representative",
                "Gender": "Male",
                "MaritalStatus": "Single",
                "Education": 2,
                "DistanceFromHome": 3,
                "MonthlyIncome": 3000,
                "PerformanceRating": 3,
                "WorkLifeBalance": 2,
                "TrainingTimesLastYear": 1,
                "manager_employee_number": None,
            }
        ]
    )

    records = to_employee_records(df, random_state=0)

    row = records.iloc[0]
    assert row["termination_date"] >= row["hire_date"]


def test_to_salary_records_annualizes_monthly_income(sample_raw_df: pd.DataFrame) -> None:
    with_managers = assign_managers(sample_raw_df)
    employee_records = to_employee_records(with_managers, random_state=0)
    salaries = to_salary_records(employee_records)

    row = salaries[salaries["source_employee_number"] == 1].iloc[0]
    assert row["amount"] == 5000 * 12
    assert row["reason"] == "initial"


def test_to_performance_review_records_scales_rating_and_respects_hire_date(
    sample_raw_df: pd.DataFrame,
) -> None:
    with_managers = assign_managers(sample_raw_df)
    employee_records = to_employee_records(with_managers, random_state=0)
    reviews = to_performance_review_records(employee_records, random_state=0)

    row = reviews[reviews["source_employee_number"] == 1].iloc[0]
    assert row["score"] == Decimal(str(round(3 * 1.25, 2)))
    assert (
        row["review_date"]
        >= employee_records.loc[employee_records["source_employee_number"] == 1, "hire_date"].iat[0]
    )


def test_to_absence_records_count_scales_with_work_life_balance(
    sample_raw_df: pd.DataFrame,
) -> None:
    with_managers = assign_managers(sample_raw_df)
    employee_records = to_employee_records(with_managers, random_state=0)
    absences = to_absence_records(employee_records, random_state=0)

    # WorkLifeBalance=3 for every seed row here -> max(0, 4-3) = 1 absence each.
    assert len(absences) == len(employee_records) * 1


def test_to_employee_feature_records_carries_every_feature_column_with_json_safe_types(
    sample_raw_df: pd.DataFrame,
) -> None:
    with_managers = assign_managers(sample_raw_df)
    employee_records = to_employee_records(with_managers, random_state=0)
    features = to_employee_feature_records(sample_raw_df, employee_records)

    assert list(features["source_employee_number"]) == list(
        employee_records["source_employee_number"]
    )
    row = features[features["source_employee_number"] == 1].iloc[0]
    for column in FEATURE_COLUMNS:
        assert isinstance(row[column], float | str)
    assert row["JobLevel"] == 4.0
    assert row["Department"] == "Research & Development"


def test_to_employee_training_records_count_matches_training_times_last_year(
    sample_raw_df: pd.DataFrame,
) -> None:
    with_managers = assign_managers(sample_raw_df)
    employee_records = to_employee_records(with_managers, random_state=0)
    enrollments = to_employee_training_records(employee_records, random_state=0)

    counts = enrollments.groupby("source_employee_number").size()
    assert (counts == 2).all()  # TrainingTimesLastYear=2 for every seed row
