"""Training data loading: reuses the ETL's extract/validate/clean/augment
stages (not the DB-load stage — training reads engineered features
directly, the same way the ETL pipeline holds them in memory before
mapping them onto our relational schema)."""

from pathlib import Path

import pandas as pd

from ml.etl.clean import clean
from ml.etl.extract import extract
from ml.etl.schema import RawAttritionSchema
from ml.etl.synthetic import augment

DEFAULT_SEED_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "raw" / "WA_Fn-UseC_-HR-Employee-Attrition.csv"
)


def load_training_frame(
    input_path: Path = DEFAULT_SEED_PATH,
    *,
    target_rows: int,
    random_state: int = 42,
) -> pd.DataFrame:
    raw_df = extract(input_path)
    validated_df = RawAttritionSchema.validate(raw_df, lazy=True)
    cleaned_df = clean(validated_df)
    augmented_df = augment(cleaned_df, target_rows=target_rows, random_state=random_state)
    return augmented_df.drop(columns=["is_outlier"], errors="ignore")
