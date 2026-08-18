"""Shared fixtures for ETL tests: a small DataFrame valid against
RawAttritionSchema, used across schema/synthetic/transform test modules."""

import pandas as pd
import pytest

# db_connection/db_session are defined in backend/tests/conftest.py, which
# only applies to that directory tree — re-exported here so ml/tests (a
# sibling tree) can use the same rolled-back-transaction DB fixtures.
from tests.conftest import db_connection, db_session  # noqa: F401


def _row(employee_number: int, **overrides: object) -> dict[str, object]:
    base = {
        "Age": 35,
        "Attrition": "No",
        "BusinessTravel": "Travel_Rarely",
        "DailyRate": 800,
        "Department": "Research & Development",
        "DistanceFromHome": 5,
        "Education": 3,
        "EducationField": "Life Sciences",
        "EmployeeNumber": employee_number,
        "EnvironmentSatisfaction": 3,
        "Gender": "Female",
        "HourlyRate": 60,
        "JobInvolvement": 3,
        "JobLevel": 2,
        "JobRole": "Research Scientist",
        "JobSatisfaction": 3,
        "MaritalStatus": "Married",
        "MonthlyIncome": 5000,
        "NumCompaniesWorked": 1,
        "OverTime": "No",
        "PercentSalaryHike": 12,
        "PerformanceRating": 3,
        "RelationshipSatisfaction": 3,
        "StockOptionLevel": 1,
        "TotalWorkingYears": 8,
        "TrainingTimesLastYear": 2,
        "WorkLifeBalance": 3,
        "YearsAtCompany": 5,
        "YearsInCurrentRole": 3,
        "YearsSinceLastPromotion": 1,
        "YearsWithCurrManager": 3,
    }
    base.update(overrides)
    return base


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """4 employees, 2 departments, a range of JobLevels and one Attrition=Yes."""
    rows = [
        _row(1, Department="Research & Development", JobLevel=4, JobRole="Research Director"),
        _row(2, Department="Research & Development", JobLevel=2),
        _row(
            3,
            Department="Sales",
            JobLevel=3,
            JobRole="Sales Executive",
            Attrition="Yes",
            YearsAtCompany=2,
        ),
        _row(4, Department="Sales", JobLevel=1, JobRole="Sales Representative"),
    ]
    return pd.DataFrame(rows)
