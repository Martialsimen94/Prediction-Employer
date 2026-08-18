"""Metric computation and diagnostic plots for a fitted binary classifier
pipeline: accuracy/precision/recall/F1/ROC AUC, confusion matrix,
calibration curve, learning curve, and feature importance."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless: these scripts never open a GUI window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    StratifiedGroupKFold,
    StratifiedKFold,
    cross_val_score,
    learning_curve,
)
from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class EvaluationResult:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    confusion_matrix: list[list[int]] = field(default_factory=list)
    cv_roc_auc_mean: float = 0.0
    cv_roc_auc_std: float = 0.0

    def as_mlflow_metrics(self) -> dict[str, float]:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "cv_roc_auc_mean": self.cv_roc_auc_mean,
            "cv_roc_auc_std": self.cv_roc_auc_std,
        }


def cross_validate_roc_auc(
    pipeline: Pipeline,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    *,
    cv_folds: int = 5,
    groups: pd.Series | None = None,
) -> tuple[float, float]:
    """`groups` (typically the synthetic-augmentation lineage_id, see
    ml/etl/synthetic.py) keeps a row and its close synthetic relatives in
    the same fold — StratifiedKFold alone would let a model "recognize"
    a near-duplicate of a training row in its validation fold and report
    an inflated score. Falls back to plain StratifiedKFold when no groups
    are given (e.g. data with no synthetic lineage to group by)."""
    cv = (
        StratifiedGroupKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        if groups is not None
        else StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    )
    scores = cross_val_score(
        pipeline, x_train, y_train, cv=cv, groups=groups, scoring="roc_auc", n_jobs=-1
    )
    return float(scores.mean()), float(scores.std())


def evaluate(
    pipeline: Pipeline,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    *,
    cv_folds: int = 5,
    cv_groups: pd.Series | None = None,
) -> EvaluationResult:
    y_pred = pipeline.predict(x_test)
    y_proba = pipeline.predict_proba(x_test)[:, 1]
    cv_mean, cv_std = cross_validate_roc_auc(
        pipeline, x_train, y_train, cv_folds=cv_folds, groups=cv_groups
    )

    return EvaluationResult(
        accuracy=accuracy_score(y_test, y_pred),
        precision=precision_score(y_test, y_pred, zero_division=0),
        recall=recall_score(y_test, y_pred, zero_division=0),
        f1=f1_score(y_test, y_pred, zero_division=0),
        roc_auc=roc_auc_score(y_test, y_proba),
        confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
        cv_roc_auc_mean=cv_mean,
        cv_roc_auc_std=cv_std,
    )


def plot_confusion_matrix(
    pipeline: Pipeline, x_test: pd.DataFrame, y_test: pd.Series, path: Path
) -> Path:
    fig, ax = plt.subplots(figsize=(5, 5))
    ConfusionMatrixDisplay.from_estimator(
        pipeline, x_test, y_test, display_labels=["Stayed", "Left"], ax=ax, colorbar=False
    )
    ax.set_title("Confusion Matrix")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_calibration_curve(
    pipeline: Pipeline, x_test: pd.DataFrame, y_test: pd.Series, path: Path
) -> Path:
    y_proba = pipeline.predict_proba(x_test)[:, 1]
    prob_true, prob_pred = calibration_curve(y_test, y_proba, n_bins=10, strategy="quantile")

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(prob_pred, prob_true, marker="o", label="Model")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfectly calibrated")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Calibration Curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_learning_curve(
    pipeline: Pipeline,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    path: Path,
    *,
    groups: pd.Series | None = None,
) -> Path:
    cv = (
        StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
        if groups is not None
        else StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    )
    train_sizes, train_scores, val_scores = learning_curve(
        pipeline,
        x_train,
        y_train,
        groups=groups,
        cv=cv,
        scoring="roc_auc",
        train_sizes=np.linspace(0.1, 1.0, 5),
        n_jobs=-1,
    )

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(train_sizes, train_scores.mean(axis=1), marker="o", label="Training score")
    ax.plot(train_sizes, val_scores.mean(axis=1), marker="o", label="Validation score")
    ax.set_xlabel("Training examples")
    ax.set_ylabel("ROC AUC")
    ax.set_title("Learning Curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_feature_importance(
    pipeline: Pipeline, feature_names: list[str], path: Path, *, top_n: int = 20
) -> Path | None:
    estimator = pipeline.named_steps["classifier"]
    importances: Any = getattr(estimator, "feature_importances_", None)
    if importances is None:
        return None

    order = np.argsort(importances)[::-1][:top_n]
    top_features = [feature_names[i] for i in order]
    top_importances = importances[order]

    fig, ax = plt.subplots(figsize=(7, max(4, len(top_features) * 0.3)))
    ax.barh(top_features[::-1], top_importances[::-1])
    ax.set_xlabel("Importance")
    ax.set_title("Feature Importance")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path
