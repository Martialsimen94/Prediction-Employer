"""Integration tests for the reporting endpoints (Module 11), backed by
the `db/sql` views/function (Module 2)."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.main import app
from app.models.ml import AttritionPrediction
from tests.auth_test_helpers import auth_header_for_role


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def hr_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="hr", email="hr-reports@example.com")


@pytest.fixture
def executive_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="executive", email="exec-reports@example.com")


@pytest.fixture
def employee_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="employee", email="plain-reports@example.com")


@pytest.fixture
def department_id(client: TestClient, hr_headers: dict[str, str]) -> int:
    token = uuid.uuid4().hex[:8]
    response = client.post(
        "/api/v1/departments", json={"name": f"Reports Dept {token}"}, headers=hr_headers
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def employee_id(client: TestClient, hr_headers: dict[str, str], department_id: int) -> int:
    token = uuid.uuid4().hex[:8]
    response = client.post(
        "/api/v1/employees",
        json={
            "employee_number": f"E-RPT-{token}",
            "first_name": "Reeva",
            "last_name": "Ports",
            "email": f"reeva-{token}@example.com",
            "hire_date": "2020-01-15",
            "job_title": "Analyst",
            "department_id": department_id,
        },
        headers=hr_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _add_prediction(
    db_session: Session, *, employee_id: int, risk_level: str, risk_score: str
) -> None:
    db_session.add(
        AttritionPrediction(
            employee_id=employee_id,
            risk_score=risk_score,
            risk_level=risk_level,
            predicted_at=datetime.now(UTC),
            top_features={"OverTime": 0.4},
            shap_values={"OverTime": 0.4},
        )
    )
    db_session.flush()


def test_department_kpis_reflects_created_employees(
    client: TestClient, hr_headers: dict[str, str], department_id: int, employee_id: int
) -> None:
    response = client.get("/api/v1/reports/department-kpis", headers=hr_headers)
    assert response.status_code == 200
    row = next(r for r in response.json() if r["department_id"] == department_id)
    assert row["active_headcount"] == 1
    assert "turnover_rate_12mo" in row


def test_risk_distribution_counts_latest_predictions(
    client: TestClient,
    executive_headers: dict[str, str],
    db_session: Session,
    employee_id: int,
) -> None:
    _add_prediction(db_session, employee_id=employee_id, risk_level="high", risk_score="0.6000")

    response = client.get("/api/v1/reports/risk-distribution", headers=executive_headers)
    assert response.status_code == 200
    assert response.json()["high"] == 1
    assert response.json()["low"] == 0


def test_attrition_risk_summary_filters_by_risk_level(
    client: TestClient,
    executive_headers: dict[str, str],
    db_session: Session,
    employee_id: int,
) -> None:
    _add_prediction(db_session, employee_id=employee_id, risk_level="critical", risk_score="0.9000")

    matching = client.get(
        "/api/v1/reports/attrition-risk-summary?risk_level=critical", headers=executive_headers
    )
    assert matching.status_code == 200
    assert matching.json()["total"] == 1
    assert matching.json()["items"][0]["employee_id"] == employee_id

    non_matching = client.get(
        "/api/v1/reports/attrition-risk-summary?risk_level=low", headers=executive_headers
    )
    assert non_matching.json()["total"] == 0


def test_attrition_risk_summary_filters_by_manager(
    client: TestClient,
    hr_headers: dict[str, str],
    executive_headers: dict[str, str],
    db_session: Session,
    department_id: int,
    employee_id: int,
) -> None:
    manager = client.post(
        "/api/v1/employees",
        json={
            "employee_number": f"E-MGR-{uuid.uuid4().hex[:8]}",
            "first_name": "Mo",
            "last_name": "Boss",
            "email": f"mo-{uuid.uuid4().hex[:8]}@example.com",
            "hire_date": "2018-01-15",
            "job_title": "Manager",
            "department_id": department_id,
        },
        headers=hr_headers,
    ).json()

    client.patch(
        f"/api/v1/employees/{employee_id}",
        json={"manager_id": manager["id"]},
        headers=hr_headers,
    )
    _add_prediction(db_session, employee_id=employee_id, risk_level="high", risk_score="0.6000")

    response = client.get(
        f"/api/v1/reports/attrition-risk-summary?manager_id={manager['id']}",
        headers=executive_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_employee_360_view(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    response = client.get(f"/api/v1/reports/employees/{employee_id}/360", headers=hr_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == employee_id
    assert body["latest_attrition_risk_level"] is None


def test_employee_360_for_missing_employee_is_404(
    client: TestClient, hr_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/reports/employees/999999/360", headers=hr_headers)
    assert response.status_code == 404


def test_reports_require_a_permission(client: TestClient, employee_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/reports/department-kpis", headers=employee_headers)
    assert response.status_code == 403
