"""Unit tests for syncing an MLflow-loaded model into the backend's
`ml_model_registry` table (the FK target for persisted predictions)."""

from sqlalchemy.orm import Session

from app.models.ml import MLModelRegistry
from ml.inference.model_loader import LoadedModel, get_or_create_registry_entry


def _loaded(run_id: str) -> LoadedModel:
    return LoadedModel(
        pipeline=None,  # type: ignore[arg-type]
        run_id=run_id,
        version="3",
        algorithm="random_forest",
        metrics={"roc_auc": 0.8},
    )


def test_get_or_create_registry_entry_creates_once(db_session: Session) -> None:
    loaded = _loaded("run-abc")

    entry = get_or_create_registry_entry(db_session, loaded)

    assert entry.mlflow_run_id == "run-abc"
    assert entry.version == "3"
    assert entry.metrics == {"roc_auc": 0.8}


def test_get_or_create_registry_entry_is_idempotent(db_session: Session) -> None:
    loaded = _loaded("run-xyz")

    first = get_or_create_registry_entry(db_session, loaded)
    second = get_or_create_registry_entry(db_session, loaded)

    assert first.id == second.id
    assert db_session.query(MLModelRegistry).filter_by(mlflow_run_id="run-xyz").count() == 1
