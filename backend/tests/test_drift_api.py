"""Integration tests for the data drift report API (Module 10).

`check_drift_and_retrain_task.delay()` is monkeypatched to a no-op, same
idea as the notifications tests (see test_notifications_and_audit_api.py):
the actual Celery task (drift detection + a potential full retrain) is
exercised separately in ml/tests/test_monitoring_*.py, not through the API.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.main import app
from app.models.ml import DataDriftReport
from tests.auth_test_helpers import auth_header_for_role


@pytest.fixture(autouse=True)
def _no_real_celery_dispatch() -> Generator[None, None, None]:
    with patch("app.services.monitoring_service.check_drift_and_retrain_task.delay"):
        yield


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def hr_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="hr", email="hr-drift@example.com")


@pytest.fixture
def ds_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="data_scientist", email="ds-drift@example.com")


def _add_report(db_session: Session, *, feature_name: str, drift_detected: bool) -> None:
    db_session.add(
        DataDriftReport(
            feature_name=feature_name,
            reference_period_start="2024-01-01",
            reference_period_end="2024-01-01",
            current_period_start="2024-03-01",
            current_period_end="2024-03-01",
            drift_score="0.30000" if drift_detected else "0.01000",
            drift_detected=drift_detected,
            method="psi",
            generated_at=datetime.now(UTC),
        )
    )
    db_session.flush()


def test_list_drift_reports(
    client: TestClient, hr_headers: dict[str, str], db_session: Session
) -> None:
    _add_report(db_session, feature_name="OverTime", drift_detected=True)
    _add_report(db_session, feature_name="MonthlyIncome", drift_detected=False)

    response = client.get("/api/v1/drift-reports", headers=hr_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_list_drift_reports_filters_by_drift_detected(
    client: TestClient, hr_headers: dict[str, str], db_session: Session
) -> None:
    _add_report(db_session, feature_name="OverTime", drift_detected=True)
    _add_report(db_session, feature_name="MonthlyIncome", drift_detected=False)

    response = client.get("/api/v1/drift-reports?drift_detected=true", headers=hr_headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["feature_name"] == "OverTime"


def test_data_scientist_can_trigger_a_drift_check(
    client: TestClient, ds_headers: dict[str, str]
) -> None:
    response = client.post("/api/v1/drift-reports/check", headers=ds_headers)
    assert response.status_code == 202
    assert response.json() == {"status": "scheduled"}


def test_hr_cannot_trigger_a_drift_check(client: TestClient, hr_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/drift-reports/check", headers=hr_headers)
    assert response.status_code == 403
