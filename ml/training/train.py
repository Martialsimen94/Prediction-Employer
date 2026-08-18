"""Train, tune, evaluate and compare every candidate model; track everything
in MLflow; register the best one in the model registry.

    PYTHONPATH=backend poetry run python -m ml.training.train \
        --target-rows 5000 --n-trials 12

Use --quick for a fast correctness check (small sample, few trials) before
committing to a full run.
"""

import argparse
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import mlflow
import mlflow.sklearn
import optuna
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.pipeline import Pipeline

from ml.etl.features import build_feature_pipeline, split_features_and_target
from ml.training import evaluate as eval_stage
from ml.training.data import DEFAULT_SEED_PATH, load_training_frame
from ml.training.evaluate import EvaluationResult
from ml.training.mlflow_utils import REGISTERED_MODEL_NAME, configure_mlflow
from ml.training.models import MODEL_SPECS, RANDOM_STATE, ModelSpec

optuna.logging.set_verbosity(optuna.logging.WARNING)


@dataclass(frozen=True)
class TrainedModel:
    name: str
    run_id: str
    model_uri: str
    result: EvaluationResult
    pipeline: Pipeline


def _build_objective(
    spec: ModelSpec,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    cv_folds: int,
    groups_train: pd.Series,
) -> Callable[[optuna.Trial], float]:
    def objective(trial: optuna.Trial) -> float:
        params = spec.suggest_params(trial)
        pipeline = Pipeline(
            [("preprocess", build_feature_pipeline()), ("classifier", spec.build(params))]
        )
        # Grouped by synthetic-augmentation lineage (see ml/etl/synthetic.py) so a
        # row and its near-duplicate relatives never straddle a fold boundary.
        cv = StratifiedGroupKFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_STATE)
        scores = cross_val_score(
            pipeline, x_train, y_train, cv=cv, groups=groups_train, scoring="roc_auc", n_jobs=1
        )
        return float(scores.mean())

    return objective


def train_one_model(
    spec: ModelSpec,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    groups_train: pd.Series,
    *,
    n_trials: int,
    tuning_cv_folds: int,
    final_cv_folds: int,
) -> TrainedModel:
    objective = _build_objective(spec, x_train, y_train, tuning_cv_folds, groups_train)
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    pipeline = Pipeline(
        [
            ("preprocess", build_feature_pipeline()),
            ("classifier", spec.build(dict(study.best_params))),
        ]
    )
    pipeline.fit(x_train, y_train)

    result = eval_stage.evaluate(
        pipeline,
        x_train,
        y_train,
        x_test,
        y_test,
        cv_folds=final_cv_folds,
        cv_groups=groups_train,
    )

    with mlflow.start_run(run_name=spec.name):
        mlflow.log_params({f"best_{k}": v for k, v in study.best_params.items()})
        mlflow.log_param("n_trials", n_trials)
        mlflow.log_param("model_type", spec.name)
        mlflow.log_metrics(result.as_mlflow_metrics())

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mlflow.log_artifact(
                str(
                    eval_stage.plot_confusion_matrix(
                        pipeline, x_test, y_test, tmp_path / "confusion_matrix.png"
                    )
                )
            )
            mlflow.log_artifact(
                str(
                    eval_stage.plot_calibration_curve(
                        pipeline, x_test, y_test, tmp_path / "calibration_curve.png"
                    )
                )
            )
            mlflow.log_artifact(
                str(
                    eval_stage.plot_learning_curve(
                        pipeline,
                        x_train,
                        y_train,
                        tmp_path / "learning_curve.png",
                        groups=groups_train,
                    )
                )
            )
            if spec.supports_feature_importance:
                feature_names = list(pipeline.named_steps["preprocess"].get_feature_names_out())
                importance_path = eval_stage.plot_feature_importance(
                    pipeline, feature_names, tmp_path / "feature_importance.png"
                )
                if importance_path is not None:
                    mlflow.log_artifact(str(importance_path))

        model_info = mlflow.sklearn.log_model(
            pipeline, artifact_path="model", input_example=x_train.head(3)
        )
        active_run = mlflow.active_run()
        assert active_run is not None  # we're inside the `with mlflow.start_run()` block
        run_id = active_run.info.run_id

    return TrainedModel(
        name=spec.name,
        run_id=run_id,
        model_uri=model_info.model_uri,
        result=result,
        pipeline=pipeline,
    )


def run(
    *,
    input_path: Path = DEFAULT_SEED_PATH,
    target_rows: int,
    n_trials: int,
    tuning_cv_folds: int = 3,
    final_cv_folds: int = 5,
    tracking_uri: str | None = None,
) -> list[TrainedModel]:
    configure_mlflow(tracking_uri)

    df = load_training_frame(input_path, target_rows=target_rows)
    x, y = split_features_and_target(df)
    groups = df["lineage_id"]

    # A plain stratified train_test_split would let a synthetic row and its
    # real "parent" (or another jittered sibling) land on opposite sides of
    # the split, inflating test scores — group by lineage_id instead (5
    # groups-aware folds, one held out as test) to prevent that leakage.
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    train_idx, test_idx = next(splitter.split(x, y, groups))
    x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    groups_train = groups.iloc[train_idx]

    runs = [
        train_one_model(
            spec,
            x_train,
            y_train,
            x_test,
            y_test,
            groups_train,
            n_trials=n_trials,
            tuning_cv_folds=tuning_cv_folds,
            final_cv_folds=final_cv_folds,
        )
        for spec in MODEL_SPECS
    ]

    best = max(runs, key=lambda r: r.result.roc_auc)
    registered = mlflow.register_model(best.model_uri, REGISTERED_MODEL_NAME)
    client = mlflow.MlflowClient()
    # Aliases replace the deprecated stage-based registry API (MLflow 2.9+):
    # https://mlflow.org/docs/latest/model-registry.html#migrating-from-stages
    client.set_registered_model_alias(
        name=REGISTERED_MODEL_NAME, alias="staging", version=registered.version
    )

    return runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_SEED_PATH)
    parser.add_argument("--target-rows", type=int, default=5000)
    parser.add_argument("--n-trials", type=int, default=12)
    parser.add_argument("--quick", action="store_true", help="fast correctness check")
    args = parser.parse_args()

    target_rows = 200 if args.quick else args.target_rows
    n_trials = 3 if args.quick else args.n_trials

    runs = run(input_path=args.input, target_rows=target_rows, n_trials=n_trials)

    print(f"{'model':<20} {'roc_auc':>8} {'f1':>8} {'accuracy':>10} {'cv_auc_mean':>12}")  # noqa: T201
    for r in sorted(runs, key=lambda r: r.result.roc_auc, reverse=True):
        result = r.result
        print(  # noqa: T201
            f"{r.name:<20} {result.roc_auc:>8.4f} {result.f1:>8.4f} "
            f"{result.accuracy:>10.4f} {result.cv_roc_auc_mean:>12.4f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
