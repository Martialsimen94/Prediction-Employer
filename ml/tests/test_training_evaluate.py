"""Unit tests for metric computation and diagnostic plots."""

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ml.etl.features import build_feature_pipeline, split_features_and_target
from ml.training.evaluate import (
    evaluate,
    plot_calibration_curve,
    plot_confusion_matrix,
    plot_feature_importance,
    plot_learning_curve,
)


def _fitted_pipeline_and_splits(
    sample_raw_df: pd.DataFrame,
) -> tuple[Pipeline, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    df = pd.concat([sample_raw_df] * 10, ignore_index=True)
    x, y = split_features_and_target(df)
    x_train, y_train = x.iloc[: len(x) // 2], y.iloc[: len(y) // 2]
    x_test, y_test = x.iloc[len(x) // 2 :], y.iloc[len(y) // 2 :]

    pipeline = Pipeline(
        [
            ("preprocess", build_feature_pipeline()),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(x_train, y_train)
    return pipeline, x_train, y_train, x_test, y_test


def test_evaluate_returns_metrics_in_valid_ranges(sample_raw_df: pd.DataFrame) -> None:
    pipeline, x_train, y_train, x_test, y_test = _fitted_pipeline_and_splits(sample_raw_df)

    result = evaluate(pipeline, x_train, y_train, x_test, y_test, cv_folds=2)

    for metric in (result.accuracy, result.precision, result.recall, result.f1, result.roc_auc):
        assert 0.0 <= metric <= 1.0
    assert len(result.confusion_matrix) == 2
    assert 0.0 <= result.cv_roc_auc_mean <= 1.0


def test_plot_confusion_matrix_writes_a_file(sample_raw_df: pd.DataFrame, tmp_path: Path) -> None:
    pipeline, _, _, x_test, y_test = _fitted_pipeline_and_splits(sample_raw_df)

    path = plot_confusion_matrix(pipeline, x_test, y_test, tmp_path / "cm.png")

    assert path.exists()
    assert path.stat().st_size > 0


def test_plot_calibration_curve_writes_a_file(sample_raw_df: pd.DataFrame, tmp_path: Path) -> None:
    pipeline, _, _, x_test, y_test = _fitted_pipeline_and_splits(sample_raw_df)

    path = plot_calibration_curve(pipeline, x_test, y_test, tmp_path / "calibration.png")

    assert path.exists()


def test_plot_learning_curve_writes_a_file(sample_raw_df: pd.DataFrame, tmp_path: Path) -> None:
    pipeline, x_train, y_train, _, _ = _fitted_pipeline_and_splits(sample_raw_df)

    path = plot_learning_curve(pipeline, x_train, y_train, tmp_path / "learning.png")

    assert path.exists()


def test_plot_feature_importance_returns_none_without_importances(
    sample_raw_df: pd.DataFrame, tmp_path: Path
) -> None:
    pipeline, _, _, x_test, _ = _fitted_pipeline_and_splits(sample_raw_df)
    feature_names = list(pipeline.named_steps["preprocess"].get_feature_names_out())

    # LogisticRegression has no feature_importances_ attribute.
    result = plot_feature_importance(pipeline, feature_names, tmp_path / "importance.png")

    assert result is None
