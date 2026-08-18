"""Candidate models and their Optuna hyperparameter search spaces."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import optuna
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier

RANDOM_STATE = 42


@dataclass(frozen=True)
class ModelSpec:
    name: str
    build: Callable[[dict[str, Any]], ClassifierMixin]
    suggest_params: Callable[[optuna.Trial], dict[str, Any]]
    supports_feature_importance: bool = False


def _logistic_regression(params: dict[str, Any]) -> ClassifierMixin:
    return LogisticRegression(max_iter=2000, random_state=RANDOM_STATE, **params)


def _logistic_regression_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "C": trial.suggest_float("C", 1e-3, 10.0, log=True),
        "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"]),
    }


def _random_forest(params: dict[str, Any]) -> ClassifierMixin:
    return RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1, **params)


def _random_forest_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 20),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"]),
    }


def _xgboost(params: dict[str, Any]) -> ClassifierMixin:
    return XGBClassifier(
        random_state=RANDOM_STATE,
        eval_metric="logloss",
        n_jobs=-1,
        **params,
    )


def _xgboost_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 2, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
    }


def _lightgbm(params: dict[str, Any]) -> ClassifierMixin:
    return LGBMClassifier(random_state=RANDOM_STATE, n_jobs=-1, verbosity=-1, **params)


def _lightgbm_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 2, 12),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 15, 127),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
    }


def _catboost(params: dict[str, Any]) -> ClassifierMixin:
    return CatBoostClassifier(random_state=RANDOM_STATE, verbose=False, **params)


def _catboost_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "iterations": trial.suggest_int("iterations", 100, 400, step=50),
        "depth": trial.suggest_int("depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 10.0),
    }


def _neural_network(params: dict[str, Any]) -> ClassifierMixin:
    hidden_layer_sizes = (params.pop("hidden_layer_size"),) * params.pop("n_hidden_layers")
    return MLPClassifier(
        hidden_layer_sizes=hidden_layer_sizes,
        random_state=RANDOM_STATE,
        max_iter=500,
        early_stopping=True,
        **params,
    )


def _neural_network_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "hidden_layer_size": trial.suggest_int("hidden_layer_size", 16, 128, step=16),
        "n_hidden_layers": trial.suggest_int("n_hidden_layers", 1, 2),
        "alpha": trial.suggest_float("alpha", 1e-5, 1e-1, log=True),
        "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True),
    }


MODEL_SPECS: list[ModelSpec] = [
    ModelSpec("logistic_regression", _logistic_regression, _logistic_regression_params),
    ModelSpec("random_forest", _random_forest, _random_forest_params, True),
    ModelSpec("xgboost", _xgboost, _xgboost_params, True),
    ModelSpec("lightgbm", _lightgbm, _lightgbm_params, True),
    ModelSpec("catboost", _catboost, _catboost_params, True),
    ModelSpec("neural_network", _neural_network, _neural_network_params),
]
