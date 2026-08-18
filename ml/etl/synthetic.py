"""Synthetic augmentation: scale a small real seed dataset up to an
"enterprise" size while preserving its real joint statistics.

Each synthetic row is a bootstrap resample of a real seed row (not an
independent per-column resample, which would destroy correlations like
"low JobSatisfaction + OverTime=Yes correlates with Attrition=Yes") with
numeric columns jittered by a small random percentage so rows aren't exact
duplicates. EmployeeNumber is reassigned to a fresh, non-overlapping range.
"""

import numpy as np
import pandas as pd

JITTER_COLUMNS = [
    "Age",
    "DailyRate",
    "DistanceFromHome",
    "HourlyRate",
    "MonthlyIncome",
    "PercentSalaryHike",
    "TotalWorkingYears",
    "YearsAtCompany",
    "YearsInCurrentRole",
    "YearsSinceLastPromotion",
    "YearsWithCurrManager",
]

# Columns whose valid range is bounded (rounded/int, non-negative); jitter must not push
# a value below its floor. Age also has a soft ceiling to stay realistic.
_FLOORS = {column: 0 for column in JITTER_COLUMNS} | {"Age": 18}
_CEILINGS = {"Age": 75}

JITTER_STD_FRACTION = 0.08


def augment(
    seed_df: pd.DataFrame, *, target_rows: int, random_state: int | None = None
) -> pd.DataFrame:
    """Return seed_df plus (target_rows - len(seed_df)) synthetic rows,
    row order shuffled. If target_rows <= len(seed_df), returns seed_df
    unchanged (this function only grows the dataset, never shrinks it)."""
    if target_rows <= len(seed_df):
        return seed_df.reset_index(drop=True)

    rng = np.random.default_rng(random_state)
    n_synthetic = target_rows - len(seed_df)

    sampled_indices = rng.integers(0, len(seed_df), size=n_synthetic)
    synthetic = seed_df.iloc[sampled_indices].reset_index(drop=True).copy()

    for column in JITTER_COLUMNS:
        if column not in synthetic.columns:
            continue
        noise = rng.normal(loc=1.0, scale=JITTER_STD_FRACTION, size=len(synthetic))
        jittered = (synthetic[column].to_numpy() * noise).round().astype(int)
        floor = _FLOORS.get(column, 0)
        ceiling = _CEILINGS.get(column)
        jittered = np.clip(jittered, floor, ceiling)
        synthetic[column] = jittered

    max_employee_number = seed_df["EmployeeNumber"].max()
    synthetic["EmployeeNumber"] = range(
        max_employee_number + 1, max_employee_number + 1 + n_synthetic
    )

    combined = pd.concat([seed_df, synthetic], ignore_index=True)
    return combined.sample(frac=1, random_state=random_state).reset_index(drop=True)
