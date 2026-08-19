"""Per-feature data drift detection between two `employee_feature_snapshots`
periods (see ml/etl/features.py for FEATURE_COLUMNS): a Kolmogorov-Smirnov
two-sample test for numeric features, a Population Stability Index for
categorical ones. Findings are shaped to match the `data_drift_reports`
table (backend/app/models/ml.py); `ml.monitoring.reports` persists them."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from ml.etl.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES

# p < 0.05 is the conventional significance cutoff for a KS test rejecting
# "these two samples came from the same distribution".
KS_ALPHA = 0.05
# PSI > 0.25 is the conventional "significant drift" cutoff in MLOps
# practice (0.1-0.25 is usually treated as "moderate, keep watching").
PSI_DRIFT_THRESHOLD = 0.25
# Additive smoothing so a category present in one period but absent from
# the other doesn't produce a log(0) / division-by-zero in the PSI sum.
_PSI_EPSILON = 1e-4


@dataclass(frozen=True)
class DriftFinding:
    feature_name: str
    drift_score: float
    drift_detected: bool
    method: str


def _ks_drift(feature: str, reference: pd.Series, current: pd.Series) -> DriftFinding:
    statistic, pvalue = stats.ks_2samp(reference.astype(float), current.astype(float))
    return DriftFinding(
        feature_name=feature,
        drift_score=float(statistic),
        drift_detected=bool(pvalue < KS_ALPHA),
        method="ks_test",
    )


def _population_stability_index(reference: pd.Series, current: pd.Series) -> float:
    categories = sorted(set(reference.astype(str)) | set(current.astype(str)))
    ref_shares = (
        reference.astype(str).value_counts(normalize=True).reindex(categories, fill_value=0.0)
        + _PSI_EPSILON
    )
    cur_shares = (
        current.astype(str).value_counts(normalize=True).reindex(categories, fill_value=0.0)
        + _PSI_EPSILON
    )
    return float(np.sum((cur_shares - ref_shares) * np.log(cur_shares / ref_shares)))


def _categorical_drift(feature: str, reference: pd.Series, current: pd.Series) -> DriftFinding:
    psi = _population_stability_index(reference, current)
    return DriftFinding(
        feature_name=feature,
        drift_score=psi,
        drift_detected=psi > PSI_DRIFT_THRESHOLD,
        method="psi",
    )


def detect_drift(reference: pd.DataFrame, current: pd.DataFrame) -> list[DriftFinding]:
    """One `DriftFinding` per FEATURE_COLUMNS entry, comparing the same
    column across the two (already feature-frame-shaped) periods."""
    findings = [
        _ks_drift(column, reference[column], current[column]) for column in NUMERIC_FEATURES
    ]
    findings += [
        _categorical_drift(column, reference[column], current[column])
        for column in CATEGORICAL_FEATURES
    ]
    return findings
