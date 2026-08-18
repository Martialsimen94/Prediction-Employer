"""Clean: drop constant/redundant columns, impute missing values, and flag
statistical outliers (IQR method) without dropping rows — flagged rows are
still loaded, just marked, since a real HR dataset legitimately contains
some extreme-but-real values (e.g. a very long-tenured employee)."""

import pandas as pd

# Constant across every row in the source dataset (EmployeeCount, StandardHours,
# Over18) or redundant with MonthlyIncome (MonthlyRate) — no signal, dropped.
CONSTANT_OR_REDUNDANT_COLUMNS = ["EmployeeCount", "StandardHours", "Over18", "MonthlyRate"]

OUTLIER_CHECK_COLUMNS = ["MonthlyIncome", "DistanceFromHome", "TotalWorkingYears", "YearsAtCompany"]


def drop_constant_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns_present = [c for c in CONSTANT_OR_REDUNDANT_COLUMNS if c in df.columns]
    return df.drop(columns=columns_present)


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Numeric columns: median imputation. Categorical columns: mode
    imputation (falling back to "Unknown" if a column is entirely null)."""
    df = df.copy()

    numeric_columns = df.select_dtypes(include="number").columns
    df[numeric_columns] = df[numeric_columns].fillna(df[numeric_columns].median())

    categorical_columns = df.select_dtypes(include="object").columns
    for column in categorical_columns:
        if df[column].isna().any():
            mode = df[column].mode(dropna=True)
            df[column] = df[column].fillna(mode.iloc[0] if not mode.empty else "Unknown")

    return df


def flag_outliers(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Adds an `is_outlier` boolean column: True if any checked numeric
    column falls outside 1.5x the interquartile range."""
    df = df.copy()
    columns = columns if columns is not None else OUTLIER_CHECK_COLUMNS

    is_outlier = pd.Series(False, index=df.index)
    for column in columns:
        q1, q3 = df[column].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        is_outlier |= (df[column] < lower) | (df[column] > upper)

    df["is_outlier"] = is_outlier
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_constant_columns(df)
    df = handle_missing_values(df)
    df = flag_outliers(df)
    return df
