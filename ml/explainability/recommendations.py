"""Maps the SHAP-driven risk factors behind a prediction (see
ml/explainability/shap_explainer.py) onto the concrete retention actions
the platform can recommend -- salary review, training, promotion, internal
mobility, coaching, team change, workload reduction, mentoring (see
`RecommendationAction` in backend/app/models/enums.py).

Deliberately excluded from the actionable-feature map: `Gender` and
`MaritalStatus`. Even when the model finds them predictive, an HR platform
must never justify -- or appear to justify -- an intervention by a
protected/demographic attribute; only levers HR can actually act on
(compensation, workload, career development, team fit) are mapped to
recommendations. `EducationField`, `Age` and tenure counters
(`TotalWorkingYears`, `YearsAtCompany`) are excluded too: informative for
the model, but not levers HR can pull.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.models.enums import RecommendationAction, RecommendationPriority, RiskLevel

RISK_THRESHOLDS: tuple[tuple[float, RiskLevel], ...] = (
    (0.75, RiskLevel.CRITICAL),
    (0.5, RiskLevel.HIGH),
    (0.25, RiskLevel.MEDIUM),
)


def risk_level_from_score(score: float) -> RiskLevel:
    for threshold, level in RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return RiskLevel.LOW


def _money(value: Any) -> str:
    return f"${float(value):,.0f}"


ACTIONABLE_FEATURES: dict[str, RecommendationAction] = {
    "MonthlyIncome": RecommendationAction.SALARY_INCREASE,
    "DailyRate": RecommendationAction.SALARY_INCREASE,
    "HourlyRate": RecommendationAction.SALARY_INCREASE,
    "PercentSalaryHike": RecommendationAction.SALARY_INCREASE,
    "StockOptionLevel": RecommendationAction.SALARY_INCREASE,
    "TrainingTimesLastYear": RecommendationAction.TRAINING,
    "Education": RecommendationAction.TRAINING,
    "YearsSinceLastPromotion": RecommendationAction.PROMOTION,
    "PerformanceRating": RecommendationAction.PROMOTION,
    "JobLevel": RecommendationAction.PROMOTION,
    "NumCompaniesWorked": RecommendationAction.INTERNAL_MOBILITY,
    "JobRole": RecommendationAction.INTERNAL_MOBILITY,
    "YearsInCurrentRole": RecommendationAction.INTERNAL_MOBILITY,
    "JobInvolvement": RecommendationAction.COACHING,
    "JobSatisfaction": RecommendationAction.COACHING,
    "EnvironmentSatisfaction": RecommendationAction.TEAM_CHANGE,
    "Department": RecommendationAction.TEAM_CHANGE,
    "OverTime": RecommendationAction.WORKLOAD_REDUCTION,
    "BusinessTravel": RecommendationAction.WORKLOAD_REDUCTION,
    "WorkLifeBalance": RecommendationAction.WORKLOAD_REDUCTION,
    "DistanceFromHome": RecommendationAction.WORKLOAD_REDUCTION,
    "RelationshipSatisfaction": RecommendationAction.MENTORING,
    "YearsWithCurrManager": RecommendationAction.MENTORING,
}

_RATIONALES: dict[str, Callable[[Any], str]] = {
    "MonthlyIncome": lambda v: f"Monthly income of {_money(v)} lags what retention requires.",
    "DailyRate": lambda v: f"Daily rate of {_money(v)} is a below-peer compensation signal.",
    "HourlyRate": lambda v: f"Hourly rate of {_money(v)} is a below-peer compensation signal.",
    "PercentSalaryHike": (
        lambda v: f"Last salary hike of only {v:.0f}% underperforms retention needs."
    ),
    "StockOptionLevel": lambda v: f"Stock option level of {v:.0f} offers little long-term upside.",
    "TrainingTimesLastYear": (lambda v: f"Only {v:.0f} training sessions last year limits growth."),
    "Education": lambda v: f"Education level {v:.0f} suggests unmet development needs.",
    "YearsSinceLastPromotion": (
        lambda v: f"{v:.0f} years since the last promotion is a stagnation signal."
    ),
    "PerformanceRating": (
        lambda v: f"A performance rating of {v:.0f} without progression is discouraging."
    ),
    "JobLevel": lambda v: f"Job level {v:.0f} may be capping this employee's growth path.",
    "NumCompaniesWorked": (
        lambda v: f"{v:.0f} prior employers suggests a pattern of seeking new challenges."
    ),
    "JobRole": lambda v: f"Current role ({v}) may no longer fit this employee's career goals.",
    "YearsInCurrentRole": (
        lambda v: f"{v:.0f} years in the same role without a change is a stagnation signal."
    ),
    "JobInvolvement": (
        lambda v: f"Job involvement score of {v:.0f} points to low day-to-day engagement."
    ),
    "JobSatisfaction": (
        lambda v: f"Job satisfaction score of {v:.0f} is a direct attrition warning sign."
    ),
    "EnvironmentSatisfaction": (
        lambda v: f"Environment satisfaction score of {v:.0f} suggests a poor team fit."
    ),
    "Department": (
        lambda v: f"Department ({v}) context is a contributing factor; a team change may help."
    ),
    "OverTime": lambda v: f"Frequent overtime ({v}) is driving burnout risk.",
    "BusinessTravel": lambda v: f"Travel frequency ({v}) is adding strain.",
    "WorkLifeBalance": lambda v: f"Work-life balance score of {v:.0f} is a burnout warning sign.",
    "DistanceFromHome": lambda v: f"A {v:.0f} km commute is adding daily friction.",
    "RelationshipSatisfaction": (
        lambda v: (
            f"Relationship satisfaction score of {v:.0f} suggests a strained manager relationship."
        )
    ),
    "YearsWithCurrManager": (
        lambda v: f"{v:.0f} years with the same manager without a check-in is a risk signal."
    ),
}

# One priority per rank (0-indexed) at each risk level; LOW-risk employees
# get no recommendations at all -- there's no urgency to act on yet.
_PRIORITY_LADDER: dict[RiskLevel, list[RecommendationPriority]] = {
    RiskLevel.CRITICAL: [
        RecommendationPriority.HIGH,
        RecommendationPriority.HIGH,
        RecommendationPriority.MEDIUM,
    ],
    RiskLevel.HIGH: [
        RecommendationPriority.HIGH,
        RecommendationPriority.MEDIUM,
        RecommendationPriority.MEDIUM,
    ],
    RiskLevel.MEDIUM: [
        RecommendationPriority.MEDIUM,
        RecommendationPriority.LOW,
        RecommendationPriority.LOW,
    ],
    RiskLevel.LOW: [],
}


@dataclass(frozen=True)
class RecommendationSuggestion:
    action_type: RecommendationAction
    rationale: str
    priority: RecommendationPriority
    feature: str
    contribution: float


def generate_recommendations(
    top_features: dict[str, float],
    raw_row: pd.Series,
    risk_level: RiskLevel,
    *,
    max_recommendations: int = 3,
) -> list[RecommendationSuggestion]:
    """`top_features` are SHAP contributions to the positive (Attrition=Yes)
    class (see ShapExplainer.explain), `raw_row` the employee's original
    (pre-encoding) feature values. Only features that are both risk-raising
    for this employee (positive contribution) and mapped to an actionable
    lever are considered; at most one recommendation per action type."""
    ladder = _PRIORITY_LADDER[risk_level]
    if not ladder:
        return []

    risk_drivers = sorted(
        (
            (feature, contribution)
            for feature, contribution in top_features.items()
            if contribution > 0 and feature in ACTIONABLE_FEATURES
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    suggestions: list[RecommendationSuggestion] = []
    used_actions: set[RecommendationAction] = set()
    for feature, contribution in risk_drivers:
        if len(suggestions) >= max_recommendations:
            break
        action = ACTIONABLE_FEATURES[feature]
        if action in used_actions:
            continue
        used_actions.add(action)
        suggestions.append(
            RecommendationSuggestion(
                action_type=action,
                rationale=_RATIONALES[feature](raw_row[feature]),
                priority=ladder[min(len(suggestions), len(ladder) - 1)],
                feature=feature,
                contribution=contribution,
            )
        )

    return suggestions
