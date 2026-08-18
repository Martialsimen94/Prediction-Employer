"""Unit tests for the risk-level bucketing and recommendation engine."""

import pandas as pd
import pytest

from app.models.enums import RecommendationAction, RecommendationPriority, RiskLevel
from ml.explainability.recommendations import (
    _RATIONALES,
    ACTIONABLE_FEATURES,
    generate_recommendations,
    risk_level_from_score,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, RiskLevel.LOW),
        (0.24, RiskLevel.LOW),
        (0.25, RiskLevel.MEDIUM),
        (0.49, RiskLevel.MEDIUM),
        (0.5, RiskLevel.HIGH),
        (0.74, RiskLevel.HIGH),
        (0.75, RiskLevel.CRITICAL),
        (1.0, RiskLevel.CRITICAL),
    ],
)
def test_risk_level_from_score_thresholds(score: float, expected: RiskLevel) -> None:
    assert risk_level_from_score(score) == expected


def test_actionable_features_and_rationales_are_in_sync() -> None:
    assert set(ACTIONABLE_FEATURES) == set(_RATIONALES)


def test_protected_attributes_are_not_actionable() -> None:
    assert "Gender" not in ACTIONABLE_FEATURES
    assert "MaritalStatus" not in ACTIONABLE_FEATURES


def _raw_row(**overrides: object) -> pd.Series:
    # Every actionable feature gets a placeholder value so any combination
    # of top_features used across these tests can format a rationale;
    # individual tests override the ones they care about.
    base: dict[str, object] = dict.fromkeys(ACTIONABLE_FEATURES, 1)
    base["Gender"] = "Female"
    base["MaritalStatus"] = "Single"
    base.update(overrides)
    return pd.Series(base)


def test_low_risk_yields_no_recommendations() -> None:
    top_features = {"MonthlyIncome": 0.3, "OverTime": 0.2}

    recommendations = generate_recommendations(top_features, _raw_row(), RiskLevel.LOW)

    assert recommendations == []


def test_critical_risk_first_recommendation_is_high_priority() -> None:
    top_features = {"MonthlyIncome": 0.3, "OverTime": 0.2, "JobSatisfaction": 0.1}

    recommendations = generate_recommendations(top_features, _raw_row(), RiskLevel.CRITICAL)

    assert recommendations[0].priority == RecommendationPriority.HIGH
    assert recommendations[0].feature == "MonthlyIncome"
    assert recommendations[0].action_type == RecommendationAction.SALARY_INCREASE


def test_negative_and_non_actionable_contributions_are_excluded() -> None:
    top_features = {
        "MonthlyIncome": -0.4,  # negative: not a risk driver for this employee
        "Gender": 0.5,  # protected attribute: never actionable
        "OverTime": 0.2,
    }

    recommendations = generate_recommendations(top_features, _raw_row(), RiskLevel.HIGH)

    assert [r.feature for r in recommendations] == ["OverTime"]


def test_duplicate_action_types_are_deduplicated() -> None:
    # MonthlyIncome and StockOptionLevel both map to SALARY_INCREASE.
    top_features = {"MonthlyIncome": 0.5, "StockOptionLevel": 0.4, "OverTime": 0.3}

    recommendations = generate_recommendations(top_features, _raw_row(), RiskLevel.CRITICAL)

    actions = [r.action_type for r in recommendations]
    assert actions.count(RecommendationAction.SALARY_INCREASE) == 1
    assert RecommendationAction.WORKLOAD_REDUCTION in actions


def test_max_recommendations_caps_the_result_length() -> None:
    top_features = {
        "MonthlyIncome": 0.5,
        "OverTime": 0.4,
        "JobSatisfaction": 0.3,
        "YearsSinceLastPromotion": 0.2,
    }

    recommendations = generate_recommendations(
        top_features, _raw_row(), RiskLevel.CRITICAL, max_recommendations=2
    )

    assert len(recommendations) == 2
