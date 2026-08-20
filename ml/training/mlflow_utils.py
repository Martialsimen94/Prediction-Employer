"""Shared MLflow tracking configuration for training and monitoring
scripts. Defaults to a local sqlite backend store (full run/param/metric
history + model registry, no server process required) so CLI scripts work
standalone; set MLFLOW_TRACKING_URI (e.g. to the `mlflow` service's
http://mlflow:5000 in the Docker Compose stack, see docker/docker-compose.yml)
to point every service at one shared tracking server instead -- otherwise
each container would write to its own throwaway sqlite file and never see
what another container trained or promoted."""

import os
from pathlib import Path

import mlflow

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACKING_URI = f"sqlite:///{REPO_ROOT / 'mlruns.db'}"
EXPERIMENT_NAME = "attrition-prediction"
REGISTERED_MODEL_NAME = "attrition-classifier"

# Snapshotted once at import time, deliberately not re-read from os.environ
# inside configure_mlflow(): mlflow.set_tracking_uri() itself writes back to
# this same environ key as a side effect, so re-reading it per call would
# let one call's explicit/test tracking_uri leak into a later no-argument
# call within the same process.
_ENV_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI")


def configure_mlflow(tracking_uri: str | None = None) -> None:
    """`tracking_uri` lets tests point at an isolated temp store instead of
    the shared dev mlruns.db. Otherwise falls back to $MLFLOW_TRACKING_URI,
    then the local sqlite file."""
    resolved = tracking_uri or _ENV_TRACKING_URI or DEFAULT_TRACKING_URI
    mlflow.set_tracking_uri(resolved)
    mlflow.set_experiment(EXPERIMENT_NAME)
