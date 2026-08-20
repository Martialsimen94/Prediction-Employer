"""Unit tests for the tracking-URI precedence chain (explicit arg > $MLFLOW_
TRACKING_URI > local sqlite default) that docker/docker-compose.yml's
`mlflow` service and Module 13's containers rely on.

Regression coverage for a real bug: `mlflow.set_tracking_uri()` writes back
to `os.environ["MLFLOW_TRACKING_URI"]` as a side effect, so re-reading that
env var on every `configure_mlflow()` call let one call's explicit/test
tracking_uri leak into a later no-argument call in the same process. Fixed
by snapshotting the env var once at import time instead.
"""

import importlib
import os

import mlflow

from ml.training import mlflow_utils


def test_explicit_tracking_uri_wins(tmp_path) -> None:  # type: ignore[no-untyped-def]
    explicit = f"sqlite:///{tmp_path / 'explicit.db'}"
    mlflow_utils.configure_mlflow(explicit)
    assert mlflow.get_tracking_uri() == explicit


def test_default_fallback_is_not_leaked_by_a_prior_explicit_call(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """The actual regression: an explicit call followed by a no-argument
    call must land on the real default, not the previous explicit value
    (which `mlflow.set_tracking_uri` had quietly written into the
    environment)."""
    explicit = f"sqlite:///{tmp_path / 'explicit.db'}"
    mlflow_utils.configure_mlflow(explicit)
    assert mlflow.get_tracking_uri() == explicit

    mlflow_utils.configure_mlflow()
    assert mlflow.get_tracking_uri() == mlflow_utils.DEFAULT_TRACKING_URI


def test_env_var_fallback_when_no_explicit_uri_given(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "sqlite:////tmp/from-env.db")
    # _ENV_TRACKING_URI is snapshotted at import time by design (see the
    # module docstring) -- reload so this test's monkeypatched value is
    # actually picked up, exactly as it would be on a fresh process/container.
    reloaded = importlib.reload(mlflow_utils)
    try:
        reloaded.configure_mlflow()
        assert mlflow.get_tracking_uri() == "sqlite:////tmp/from-env.db"
    finally:
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
        importlib.reload(mlflow_utils)


def test_local_sqlite_default_when_nothing_else_set(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    reloaded = importlib.reload(mlflow_utils)
    try:
        reloaded.configure_mlflow()
        assert mlflow.get_tracking_uri() == reloaded.DEFAULT_TRACKING_URI
        assert os.path.isabs(reloaded.DEFAULT_TRACKING_URI.removeprefix("sqlite:///"))
    finally:
        importlib.reload(mlflow_utils)
