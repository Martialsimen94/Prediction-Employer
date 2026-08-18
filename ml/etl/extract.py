"""Extract: load HR data from a CSV or Excel file into a raw DataFrame."""

from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def extract(path: Path | str) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame. Column dtypes/values are
    not yet validated here — see schema.RawAttritionSchema."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(
        f"Unsupported file extension '{suffix}'; expected one of {SUPPORTED_EXTENSIONS}"
    )
