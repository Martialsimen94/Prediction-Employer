"""Transform: map the cleaned IBM-schema DataFrame onto records shaped like
our domain tables (employees, departments, salaries, performance reviews).

Foreign keys are resolved as *EmployeeNumber references* here (e.g. a
manager is identified by their EmployeeNumber, not a DB id yet) since the
real Postgres-assigned ids don't exist until load.py inserts the rows —
load.py is responsible for translating these into real foreign keys.
"""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from faker import Faker

EDUCATION_LEVELS = {
    1: "Below College",
    2: "College",
    3: "Bachelor",
    4: "Master",
    5: "Doctor",
}


def build_departments(df: pd.DataFrame) -> pd.DataFrame:
    names = sorted(df["Department"].unique())
    return pd.DataFrame({"name": names})


def assign_managers(df: pd.DataFrame) -> pd.DataFrame:
    """Within each department, the employee with the highest JobLevel (ties
    broken by EmployeeNumber for determinism) manages everyone else in that
    department; that same person is left without a manager of their own."""
    df = df.copy()
    df["manager_employee_number"] = pd.array([None] * len(df), dtype="object")

    for department_name, group in df.groupby("Department"):
        ranked = group.sort_values(["JobLevel", "EmployeeNumber"], ascending=[False, True])
        manager_employee_number = int(ranked.iloc[0]["EmployeeNumber"])
        report_mask = df["Department"].eq(department_name) & (
            df["EmployeeNumber"] != manager_employee_number
        )
        df.loc[report_mask, "manager_employee_number"] = manager_employee_number

    return df


def department_managers(df_with_managers: pd.DataFrame) -> dict[str, int]:
    """department name -> EmployeeNumber of that department's manager."""
    result: dict[str, int] = {}
    for department, group in df_with_managers.groupby("Department"):
        unmanaged = group[group["manager_employee_number"].isna()]
        if not unmanaged.empty:
            result[str(department)] = int(unmanaged.iloc[0]["EmployeeNumber"])
    return result


def to_employee_records(df: pd.DataFrame, *, random_state: int | None = None) -> pd.DataFrame:
    """One row per employee, field names matching app.models.employee.Employee
    (plus `department_name` and `manager_employee_number` for FK resolution)."""
    fake = Faker()
    Faker.seed(random_state)

    today = date.today()
    records = []
    for row in df.itertuples(index=False):
        first_name = fake.first_name()
        last_name = fake.last_name()
        employee_number = f"EMP-{row.EmployeeNumber:06d}"
        email = f"{first_name}.{last_name}.{row.EmployeeNumber}@example.com".lower()

        hire_date = today - timedelta(days=int(row.YearsAtCompany * 365.25))
        birth_date = today - timedelta(days=int(row.Age * 365.25))
        is_terminated = row.Attrition == "Yes"
        if is_terminated:
            # Somewhere between the day after hire and today — never before
            # hire_date, regardless of how short (post-jitter) the tenure is.
            tenure_days = max((today - hire_date).days, 1)
            days_after_hire = int(
                np.random.default_rng(row.EmployeeNumber).integers(1, tenure_days + 1)
            )
            termination_date = hire_date + timedelta(days=days_after_hire)
        else:
            termination_date = None

        records.append(
            {
                "source_employee_number": row.EmployeeNumber,
                "employee_number": employee_number,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "hire_date": hire_date,
                "birth_date": birth_date,
                "department_name": row.Department,
                "manager_employee_number": row.manager_employee_number,
                "job_title": row.JobRole,
                "employment_status": "terminated" if is_terminated else "active",
                "termination_date": termination_date,
                "gender": row.Gender,
                "marital_status": row.MaritalStatus,
                "education_level": EDUCATION_LEVELS.get(row.Education, "Bachelor"),
                "distance_from_home_km": Decimal(int(row.DistanceFromHome)),
                "monthly_income": int(row.MonthlyIncome),
                "performance_rating": int(row.PerformanceRating),
                "work_life_balance": int(row.WorkLifeBalance),
                "training_times_last_year": int(row.TrainingTimesLastYear),
            }
        )

    return pd.DataFrame.from_records(records)


def to_salary_records(employee_records: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_employee_number": employee_records["source_employee_number"],
            "amount": (employee_records["monthly_income"] * 12).apply(Decimal),
            "currency": "USD",
            "effective_date": employee_records["hire_date"],
            "reason": "initial",
        }
    )


def to_performance_review_records(
    employee_records: pd.DataFrame, *, random_state: int | None = None
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    today = date.today()
    days_ago = rng.integers(1, 180, size=len(employee_records))

    review_dates = [
        max(today - timedelta(days=int(d)), hire)
        for d, hire in zip(days_ago, employee_records["hire_date"], strict=True)
    ]

    return pd.DataFrame(
        {
            "source_employee_number": employee_records["source_employee_number"],
            "review_date": review_dates,
            "review_period": "Most recent cycle",
            "score": (employee_records["performance_rating"] * 1.25).apply(
                lambda v: Decimal(str(round(v, 2)))
            ),
        }
    )


# Absences and trainings aren't in the source dataset at all (unlike
# salary/performance, which map from real columns) — they're synthesized
# from a plausible signal already in the data (WorkLifeBalance,
# TrainingTimesLastYear) so the fuller schema has *something* to query,
# clearly heuristic rather than presented as real history.

ABSENCE_TYPES = ["sick", "vacation", "unpaid", "other"]
ABSENCE_TYPE_WEIGHTS = [0.55, 0.30, 0.10, 0.05]


def to_absence_records(
    employee_records: pd.DataFrame, *, random_state: int | None = None
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    today = date.today()
    columns = ["source_employee_number", "absence_type", "start_date", "end_date", "approved"]
    records = []

    for row in employee_records.itertuples(index=False):
        n_absences = max(0, 4 - row.work_life_balance)
        for _ in range(n_absences):
            start = today - timedelta(days=int(rng.integers(1, 365)))
            end = start + timedelta(days=int(rng.integers(1, 6)))
            records.append(
                {
                    "source_employee_number": row.source_employee_number,
                    "absence_type": str(rng.choice(ABSENCE_TYPES, p=ABSENCE_TYPE_WEIGHTS)),
                    "start_date": start,
                    "end_date": end,
                    "approved": bool(rng.random() < 0.9),
                }
            )

    return pd.DataFrame.from_records(records, columns=columns)


TRAINING_CATALOG = [
    ("Effective Communication", "Internal L&D", "Soft Skills", 4),
    ("Advanced Excel", "Internal L&D", "Technical", 6),
    ("Leadership Fundamentals", "Internal L&D", "Leadership", 8),
    ("Data Privacy & Compliance", "Internal L&D", "Compliance", 2),
    ("Project Management Essentials", "External Provider", "Management", 12),
    ("Conflict Resolution", "Internal L&D", "Soft Skills", 3),
    ("Advanced SQL", "External Provider", "Technical", 8),
    ("Diversity & Inclusion", "Internal L&D", "Compliance", 2),
    ("Negotiation Skills", "External Provider", "Soft Skills", 4),
    ("Time Management", "Internal L&D", "Productivity", 3),
]

TRAINING_STATUS_CHOICES = ["completed", "in_progress", "enrolled"]
TRAINING_STATUS_WEIGHTS = [0.70, 0.20, 0.10]


def to_employee_training_records(
    employee_records: pd.DataFrame, *, random_state: int | None = None
) -> pd.DataFrame:
    """`training_index` refers to a position in TRAINING_CATALOG; load.py
    resolves it to a real training_id once the catalog is inserted."""
    rng = np.random.default_rng(random_state)
    today = date.today()
    columns = [
        "source_employee_number",
        "training_index",
        "start_date",
        "completion_date",
        "status",
        "score",
    ]
    records = []

    for row in employee_records.itertuples(index=False):
        n_trainings = min(row.training_times_last_year, len(TRAINING_CATALOG))
        if n_trainings <= 0:
            continue
        training_indices = rng.choice(len(TRAINING_CATALOG), size=n_trainings, replace=False)
        for training_index in training_indices:
            start = today - timedelta(days=int(rng.integers(1, 365)))
            status = str(rng.choice(TRAINING_STATUS_CHOICES, p=TRAINING_STATUS_WEIGHTS))
            completed = status == "completed"
            records.append(
                {
                    "source_employee_number": row.source_employee_number,
                    "training_index": int(training_index),
                    "start_date": start,
                    "completion_date": (
                        start + timedelta(days=int(rng.integers(1, 30))) if completed else None
                    ),
                    "status": status,
                    "score": Decimal(int(rng.integers(60, 101))) if completed else None,
                }
            )

    return pd.DataFrame.from_records(records, columns=columns)
