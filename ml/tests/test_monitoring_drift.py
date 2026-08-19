"""Unit tests for per-feature drift detection: KS test for numeric
features, Population Stability Index for categorical ones."""

import numpy as np
import pandas as pd
import pytest

from ml.monitoring.drift import (
    PSI_DRIFT_THRESHOLD,
    _categorical_drift,
    _ks_drift,
    _population_stability_index,
    detect_drift,
)


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(42)


def test_ks_drift_not_detected_for_identically_distributed_samples(
    rng: np.random.Generator,
) -> None:
    reference = pd.Series(rng.normal(size=500))
    current = pd.Series(rng.normal(size=500))

    finding = _ks_drift("MonthlyIncome", reference, current)

    assert finding.method == "ks_test"
    assert not finding.drift_detected


def test_ks_drift_detected_for_a_shifted_distribution(rng: np.random.Generator) -> None:
    reference = pd.Series(rng.normal(loc=0, size=500))
    current = pd.Series(rng.normal(loc=5, size=500))

    finding = _ks_drift("MonthlyIncome", reference, current)

    assert finding.drift_detected
    assert finding.drift_score > 0.5


def test_psi_is_zero_for_identical_category_shares() -> None:
    reference = pd.Series(["Yes", "No"] * 100)
    current = pd.Series(["Yes", "No"] * 100)

    assert _population_stability_index(reference, current) == pytest.approx(0.0, abs=1e-6)


def test_categorical_drift_detected_for_a_shifted_category_mix() -> None:
    reference = pd.Series(["No"] * 90 + ["Yes"] * 10)
    current = pd.Series(["No"] * 20 + ["Yes"] * 80)

    finding = _categorical_drift("OverTime", reference, current)

    assert finding.method == "psi"
    assert finding.drift_score > PSI_DRIFT_THRESHOLD
    assert finding.drift_detected


def test_detect_drift_covers_every_feature_column(rng: np.random.Generator) -> None:
    from ml.etl.features import FEATURE_COLUMNS, NUMERIC_FEATURES

    reference = pd.DataFrame(
        {
            column: rng.normal(size=50) if column in NUMERIC_FEATURES else ["A", "B"] * 25
            for column in FEATURE_COLUMNS
        }
    )
    current = reference.copy()

    findings = detect_drift(reference, current)

    assert {f.feature_name for f in findings} == set(FEATURE_COLUMNS)
    assert not any(f.drift_detected for f in findings)  # identical reference/current
