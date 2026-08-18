"""Shared MLflow tracking configuration for training and (later) monitoring
scripts. Uses a local sqlite backend store (full run/param/metric history +
model registry, no server process required) rather than the plain-file
store, which doesn't support the model registry."""

from pathlib import Path

import mlflow

REPO_ROOT = Path(__file__).resolve().parents[2]
TRACKING_URI = f"sqlite:///{REPO_ROOT / 'mlruns.db'}"
EXPERIMENT_NAME = "attrition-prediction"
REGISTERED_MODEL_NAME = "attrition-classifier"


def configure_mlflow(tracking_uri: str | None = None) -> None:
    """`tracking_uri` lets tests point at an isolated temp store instead of
    the shared dev mlruns.db."""
    mlflow.set_tracking_uri(tracking_uri or TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
