"""Synthetic augmentation: scale a small real seed dataset up to an
"enterprise" size while preserving its real joint statistics.

Each synthetic row is a bootstrap resample of a real seed row (not an
independent per-column resample, which would destroy correlations like
"low JobSatisfaction + OverTime=Yes correlates with Attrition=Yes"), with
continuous numeric columns jittered by a small random percentage and
ordinal/rating columns nudged by +-1 with some probability, so a synthetic
row isn't a near-exact duplicate of its parent. EmployeeNumber is
reassigned to a fresh, non-overlapping range.

Every output row carries a `lineage_id` (the *original* EmployeeNumber it
was sampled from, or its own for real seed rows). A model that never sees
both a row and its close synthetic relatives split across train/test can
still legitimately generalize; one that does gets an inflated score from
recognizing near-duplicates rather than the underlying pattern. Callers
MUST group train/test splits and CV folds by `lineage_id` — see
ml/training/train.py — or this column defeats its own purpose.
"""

import numpy as np
import pandas as pd

CONTINUOUS_JITTER_COLUMNS = [
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
_FLOORS = {column: 0 for column in CONTINUOUS_JITTER_COLUMNS} | {"Age": 18}
_CEILINGS = {"Age": 75}

JITTER_STD_FRACTION = 0.08

# Ordinal / rating-scale columns: nudged by +-1 (not resampled from a
# distribution — these are small discrete scales) with ORDINAL_JITTER_PROB
# probability per row, clipped to the column's valid range.
ORDINAL_JITTER_RANGES: dict[str, tuple[int, int]] = {
    "Education": (1, 5),
    "EnvironmentSatisfaction": (1, 4),
    "JobInvolvement": (1, 4),
    "JobSatisfaction": (1, 4),
    "PerformanceRating": (1, 4),
    "RelationshipSatisfaction": (1, 4),
    "WorkLifeBalance": (1, 4),
    "StockOptionLevel": (0, 3),
    "NumCompaniesWorked": (0, 50),
}
ORDINAL_JITTER_PROB = 0.35


def augment(
    seed_df: pd.DataFrame, *, target_rows: int, random_state: int | None = None
) -> pd.DataFrame:
    """Return seed_df plus (target_rows - len(seed_df)) synthetic rows,
    row order shuffled, each carrying a `lineage_id`. If target_rows <=
    len(seed_df), returns seed_df unchanged plus lineage_id (this function
    only grows the dataset, never shrinks it)."""
    seed_df = seed_df.copy()
    seed_df["lineage_id"] = seed_df["EmployeeNumber"]

    if target_rows <= len(seed_df):
        return seed_df.reset_index(drop=True)

    rng = np.random.default_rng(random_state)
    n_synthetic = target_rows - len(seed_df)

    sampled_indices = rng.integers(0, len(seed_df), size=n_synthetic)
    synthetic = seed_df.iloc[sampled_indices].reset_index(drop=True).copy()
    synthetic["lineage_id"] = synthetic["EmployeeNumber"]

    for column in CONTINUOUS_JITTER_COLUMNS:
        if column not in synthetic.columns:
            continue
        noise = rng.normal(loc=1.0, scale=JITTER_STD_FRACTION, size=len(synthetic))
        jittered = (synthetic[column].to_numpy() * noise).round().astype(int)
        floor = _FLOORS.get(column, 0)
        ceiling = _CEILINGS.get(column)
        jittered = np.clip(jittered, floor, ceiling)
        synthetic[column] = jittered

    for column, (low, high) in ORDINAL_JITTER_RANGES.items():
        if column not in synthetic.columns:
            continue
        should_jitter = rng.random(len(synthetic)) < ORDINAL_JITTER_PROB
        direction = rng.choice([-1, 1], size=len(synthetic))
        nudged = synthetic[column].to_numpy() + np.where(should_jitter, direction, 0)
        synthetic[column] = np.clip(nudged, low, high)

    max_employee_number = seed_df["EmployeeNumber"].max()
    synthetic["EmployeeNumber"] = range(
        max_employee_number + 1, max_employee_number + 1 + n_synthetic
    )

    combined = pd.concat([seed_df, synthetic], ignore_index=True)
    return combined.sample(frac=1, random_state=random_state).reset_index(drop=True)
