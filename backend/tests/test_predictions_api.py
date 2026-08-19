"""Integration tests for the attrition prediction + recommendation API
(Module 9). The MLflow-backed model load (`ml.inference.model_loader.load_pipeline`)
is monkeypatched to a small pipeline fit in-process — same idea as Celery's
`.delay()` being mocked out in the notifications tests — so these tests
don't depend on a trained MLflow registry existing in the dev environment.

The tiny training set below makes `OverTime` a near-perfect predictor of
Attrition, so a test employee with `OverTime="Yes"` reliably scores as
high risk with `OverTime` as its dominant SHAP feature (-> a
`workload_reduction` recommendation) — needed to exercise the
recommendation-status endpoint without depending on exact model output.
"""

from collections.abc import Generator
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.main import app
from app.models.employee import Employee
from app.models.ml import EmployeeFeatureSnapshot
from app.services import prediction_service
from ml.etl.features import FEATURE_COLUMNS, build_feature_pipeline, split_features_and_target
from ml.inference.model_loader import LoadedModel
from ml.tests.conftest import _row
from tests.auth_test_helpers import auth_header_for_role


def _feature_dict(**overrides: Any) -> dict[str, float | str]:
    row = _row(1, **overrides)
    return {column: row[column] for column in FEATURE_COLUMNS}


def _fitted_loaded_model() -> LoadedModel:
    rows = [
        _row(i, OverTime="Yes", Attrition="Yes")
        if i % 2 == 0
        else _row(i, OverTime="No", Attrition="No")
        for i in range(1, 41)
    ]
    df = pd.DataFrame(rows)
    x, y = split_features_and_target(df)
    pipeline = Pipeline(
        [
            ("preprocess", build_feature_pipeline()),
            ("classifier", RandomForestClassifier(n_estimators=30, random_state=0)),
        ]
    )
    pipeline.fit(x, y)
    return LoadedModel(
        pipeline=pipeline,
        run_id="test-run-1",
        version="1",
        algorithm="random_forest",
        metrics={"roc_auc": 0.99},
    )


@pytest.fixture(autouse=True)
def _mock_model(db_session: Session) -> Generator[None, None, None]:
    """Also seeds a handful of background feature snapshots (for the SHAP/LIME
    background sample) belonging to *other* employees, mirroring OverTime's
    Yes/No split above."""
    prediction_service.reset_engine_cache()
    for i in range(10):
        employee = Employee(
            employee_number=f"E-BG-{i}",
            first_name="Background",
            last_name=f"Employee{i}",
            email=f"bg-employee-{i}@example.com",
            hire_date=date(2019, 1, 1),
            job_title="Engineer",
        )
        db_session.add(employee)
        db_session.flush()
        db_session.add(
            EmployeeFeatureSnapshot(
                employee_id=employee.id,
                features=_feature_dict(OverTime="Yes" if i % 2 == 0 else "No"),
                computed_at=datetime.now(UTC),
            )
        )
    db_session.flush()

    with patch(
        "app.services.prediction_service.load_pipeline", return_value=_fitted_loaded_model()
    ):
        yield
    prediction_service.reset_engine_cache()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def hr_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="hr", email="hr-pred@example.com")


@pytest.fixture
def ds_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="data_scientist", email="ds-pred@example.com")


@pytest.fixture
def employee_id(client: TestClient, hr_headers: dict[str, str]) -> int:
    """Created by HR (`employees:write`) — `data_scientist` (see
    ROLE_PERMISSIONS in the seed migration) can trigger/read predictions
    but doesn't manage employee records."""
    response = client.post(
        "/api/v1/employees",
        json={
            "employee_number": "E-PRED1",
            "first_name": "Rae",
            "last_name": "Jetson",
            "email": "rae-pred@example.com",
            "hire_date": "2020-01-15",
            "job_title": "Staff Engineer",
        },
        headers=hr_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def high_risk_snapshot(db_session: Session, employee_id: int) -> None:
    db_session.add(
        EmployeeFeatureSnapshot(
            employee_id=employee_id,
            features=_feature_dict(OverTime="Yes"),
            computed_at=datetime.now(UTC),
        )
    )
    db_session.flush()


def test_prediction_requires_a_feature_snapshot(
    client: TestClient, ds_headers: dict[str, str], employee_id: int
) -> None:
    response = client.post(f"/api/v1/employees/{employee_id}/predictions", headers=ds_headers)
    assert response.status_code == 422


def test_hr_cannot_trigger_a_prediction(
    client: TestClient,
    hr_headers: dict[str, str],
    employee_id: int,
    high_risk_snapshot: None,
) -> None:
    response = client.post(f"/api/v1/employees/{employee_id}/predictions", headers=hr_headers)
    assert response.status_code == 403


def test_predict_persists_and_returns_risk_and_recommendations(
    client: TestClient,
    ds_headers: dict[str, str],
    hr_headers: dict[str, str],
    employee_id: int,
    high_risk_snapshot: None,
) -> None:
    created = client.post(f"/api/v1/employees/{employee_id}/predictions", headers=ds_headers)
    assert created.status_code == 201
    body = created.json()

    assert body["employee_id"] == employee_id
    assert body["model_registry_id"] is not None
    assert 0.0 <= float(body["risk_score"]) <= 1.0
    assert body["risk_level"] in {"low", "medium", "high", "critical"}
    assert body["top_features"]
    assert body["shap_values"]
    # OverTime="Yes" is a near-perfect Attrition predictor in the fitted
    # model (see `_fitted_loaded_model`), so this employee should read as
    # elevated risk with a workload_reduction recommendation attached.
    assert body["risk_level"] in {"medium", "high", "critical"}
    assert body["recommendations"]
    assert any(r["action_type"] == "workload_reduction" for r in body["recommendations"])

    listed = client.get(f"/api/v1/employees/{employee_id}/predictions", headers=hr_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    prediction_id = body["id"]
    detail = client.get(f"/api/v1/predictions/{prediction_id}", headers=hr_headers)
    assert detail.status_code == 200
    assert detail.json()["recommendations"] == body["recommendations"]


def test_update_recommendation_status(
    client: TestClient,
    ds_headers: dict[str, str],
    employee_id: int,
    high_risk_snapshot: None,
) -> None:
    created = client.post(f"/api/v1/employees/{employee_id}/predictions", headers=ds_headers)
    recommendation_id = created.json()["recommendations"][0]["id"]

    updated = client.patch(
        f"/api/v1/recommendations/{recommendation_id}",
        json={"status": "completed"},
        headers=ds_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"
    assert updated.json()["resolved_at"] is not None


def test_prediction_for_missing_employee_is_404(
    client: TestClient, ds_headers: dict[str, str]
) -> None:
    response = client.post("/api/v1/employees/999999/predictions", headers=ds_headers)
    assert response.status_code == 404
