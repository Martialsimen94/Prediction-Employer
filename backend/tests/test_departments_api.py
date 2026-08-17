"""Integration tests for the /departments endpoints."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.main import app
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
    return auth_header_for_role(db_session, role="hr", email="hr-dept@example.com")


@pytest.fixture
def employee_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="employee", email="plain-dept@example.com")


def test_create_and_get_department(client: TestClient, hr_headers: dict[str, str]) -> None:
    created = client.post("/api/v1/departments", json={"name": "Engineering"}, headers=hr_headers)
    assert created.status_code == 201
    department_id = created.json()["id"]

    fetched = client.get(f"/api/v1/departments/{department_id}", headers=hr_headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Engineering"


def test_create_department_requires_write_permission(
    client: TestClient, employee_headers: dict[str, str]
) -> None:
    response = client.post("/api/v1/departments", json={"name": "Sales"}, headers=employee_headers)
    assert response.status_code == 403


def test_duplicate_department_name_is_rejected(
    client: TestClient, hr_headers: dict[str, str]
) -> None:
    client.post("/api/v1/departments", json={"name": "Marketing"}, headers=hr_headers)
    duplicate = client.post("/api/v1/departments", json={"name": "Marketing"}, headers=hr_headers)
    assert duplicate.status_code == 409


def test_get_missing_department_is_404(client: TestClient, hr_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/departments/999999", headers=hr_headers)
    assert response.status_code == 404


def test_list_departments_paginates_and_searches(
    client: TestClient, hr_headers: dict[str, str]
) -> None:
    for name in ["Finance", "Field Operations", "Legal"]:
        client.post("/api/v1/departments", json={"name": name}, headers=hr_headers)

    all_page = client.get("/api/v1/departments?limit=2&offset=0", headers=hr_headers)
    assert all_page.status_code == 200
    body = all_page.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 2

    filtered = client.get("/api/v1/departments?search=Field", headers=hr_headers)
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["name"] == "Field Operations"


def test_update_and_delete_department(client: TestClient, hr_headers: dict[str, str]) -> None:
    created = client.post("/api/v1/departments", json={"name": "Temp Dept"}, headers=hr_headers)
    department_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/departments/{department_id}",
        json={"description": "Renamed via PATCH"},
        headers=hr_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Renamed via PATCH"

    deleted = client.delete(f"/api/v1/departments/{department_id}", headers=hr_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/departments/{department_id}", headers=hr_headers).status_code == 404


def test_department_manager_must_be_an_existing_employee(
    client: TestClient, hr_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/departments", json={"name": "Ops", "manager_id": 999999}, headers=hr_headers
    )
    assert response.status_code == 404
