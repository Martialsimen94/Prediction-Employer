"""Pandera validation schema for the raw HR attrition dataset (CSV or Excel,
IBM HR Analytics column layout).

Uses the classic DataFrameSchema/Column API rather than the class-based
DataFrameModel — the latter hits a dtype-resolution bug against this
environment's pandera 0.21.1 + Python 3.12 combination.
"""

import pandera as pa

_BUSINESS_TRAVEL = ["Non-Travel", "Travel_Rarely", "Travel_Frequently"]
_YES_NO = ["Yes", "No"]

RawAttritionSchema = pa.DataFrameSchema(
    {
        "Age": pa.Column(int, checks=pa.Check.in_range(17, 75)),
        "Attrition": pa.Column(str, checks=pa.Check.isin(_YES_NO)),
        "BusinessTravel": pa.Column(str, checks=pa.Check.isin(_BUSINESS_TRAVEL)),
        "DailyRate": pa.Column(int, checks=pa.Check.ge(0)),
        "Department": pa.Column(str),
        "DistanceFromHome": pa.Column(int, checks=pa.Check.in_range(0, 200)),
        "Education": pa.Column(int, checks=pa.Check.in_range(1, 5)),
        "EducationField": pa.Column(str),
        "EmployeeNumber": pa.Column(int, checks=pa.Check.ge(0), unique=True),
        "EnvironmentSatisfaction": pa.Column(int, checks=pa.Check.in_range(1, 4)),
        "Gender": pa.Column(str, checks=pa.Check.isin(["Male", "Female"])),
        "HourlyRate": pa.Column(int, checks=pa.Check.ge(0)),
        "JobInvolvement": pa.Column(int, checks=pa.Check.in_range(1, 4)),
        "JobLevel": pa.Column(int, checks=pa.Check.in_range(1, 5)),
        "JobRole": pa.Column(str),
        "JobSatisfaction": pa.Column(int, checks=pa.Check.in_range(1, 4)),
        "MaritalStatus": pa.Column(str, checks=pa.Check.isin(["Single", "Married", "Divorced"])),
        "MonthlyIncome": pa.Column(int, checks=pa.Check.ge(0)),
        "NumCompaniesWorked": pa.Column(int, checks=pa.Check.in_range(0, 50)),
        "OverTime": pa.Column(str, checks=pa.Check.isin(_YES_NO)),
        "PercentSalaryHike": pa.Column(int, checks=pa.Check.in_range(0, 100)),
        "PerformanceRating": pa.Column(int, checks=pa.Check.in_range(1, 4)),
        "RelationshipSatisfaction": pa.Column(int, checks=pa.Check.in_range(1, 4)),
        "StockOptionLevel": pa.Column(int, checks=pa.Check.in_range(0, 3)),
        "TotalWorkingYears": pa.Column(int, checks=pa.Check.in_range(0, 60)),
        "TrainingTimesLastYear": pa.Column(int, checks=pa.Check.in_range(0, 20)),
        "WorkLifeBalance": pa.Column(int, checks=pa.Check.in_range(1, 4)),
        "YearsAtCompany": pa.Column(int, checks=pa.Check.in_range(0, 60)),
        "YearsInCurrentRole": pa.Column(int, checks=pa.Check.in_range(0, 60)),
        "YearsSinceLastPromotion": pa.Column(int, checks=pa.Check.in_range(0, 60)),
        "YearsWithCurrManager": pa.Column(int, checks=pa.Check.in_range(0, 60)),
    },
    coerce=True,
    strict=False,  # a handful of columns (EmployeeCount, Over18, StandardHours,
    # MonthlyRate) are dropped during cleaning rather than validated here —
    # they're constant or redundant in the source dataset.
)
