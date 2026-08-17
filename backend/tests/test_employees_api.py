"""Integration tests for the /employees endpoints."""

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
    return auth_header_for_role(db_session, role="hr", email="hr-emp@example.com")


@pytest.fixture
def employee_headers(db_session: Session) -> dict[str, str]:
    return auth_header_for_role(db_session, role="employee", email="plain-emp@example.com")


def _create_employee(
    client: TestClient, headers: dict[str, str], *, number: str, email: str, **overrides: object
) -> dict:
    payload = {
        "employee_number": number,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": email,
        "hire_date": "2020-01-15",
        "job_title": "Staff Engineer",
        **overrides,
    }
    response = client.post("/api/v1/employees", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get_employee(client: TestClient, hr_headers: dict[str, str]) -> None:
    created = _create_employee(client, hr_headers, number="E-1", email="ada@example.com")

    fetched = client.get(f"/api/v1/employees/{created['id']}", headers=hr_headers)
    assert fetched.status_code == 200
    assert fetched.json()["employment_status"] == "active"


def test_create_employee_requires_write_permission(
    client: TestClient, employee_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/employees",
        json={
            "employee_number": "E-2",
            "first_name": "Grace",
            "last_name": "Hopper",
            "email": "grace@example.com",
            "hire_date": "2020-01-01",
            "job_title": "Principal Engineer",
        },
        headers=employee_headers,
    )
    assert response.status_code == 403


def test_duplicate_email_is_rejected(client: TestClient, hr_headers: dict[str, str]) -> None:
    _create_employee(client, hr_headers, number="E-3", email="dup-emp@example.com")
    response = client.post(
        "/api/v1/employees",
        json={
            "employee_number": "E-4",
            "first_name": "Other",
            "last_name": "Person",
            "email": "dup-emp@example.com",
            "hire_date": "2020-01-01",
            "job_title": "Engineer",
        },
        headers=hr_headers,
    )
    assert response.status_code == 409


def test_duplicate_employee_number_is_rejected(
    client: TestClient, hr_headers: dict[str, str]
) -> None:
    _create_employee(client, hr_headers, number="E-DUPNUM", email="a@example.com")
    response = client.post(
        "/api/v1/employees",
        json={
            "employee_number": "E-DUPNUM",
            "first_name": "Other",
            "last_name": "Person",
            "email": "b@example.com",
            "hire_date": "2020-01-01",
            "job_title": "Engineer",
        },
        headers=hr_headers,
    )
    assert response.status_code == 409


def test_employee_cannot_be_own_manager(client: TestClient, hr_headers: dict[str, str]) -> None:
    created = _create_employee(client, hr_headers, number="E-5", email="self-mgr@example.com")

    response = client.patch(
        f"/api/v1/employees/{created['id']}",
        json={"manager_id": created["id"]},
        headers=hr_headers,
    )
    assert response.status_code == 422


def test_department_and_manager_assignment(client: TestClient, hr_headers: dict[str, str]) -> None:
    dept = client.post("/api/v1/departments", json={"name": "R&D"}, headers=hr_headers).json()
    manager = _create_employee(
        client, hr_headers, number="E-MGR", email="mgr@example.com", department_id=dept["id"]
    )
    report = _create_employee(
        client,
        hr_headers,
        number="E-REPORT",
        email="report@example.com",
        department_id=dept["id"],
        manager_id=manager["id"],
    )

    fetched = client.get(f"/api/v1/employees/{report['id']}", headers=hr_headers).json()
    assert fetched["manager_id"] == manager["id"]
    assert fetched["department_id"] == dept["id"]

    listed = client.get(f"/api/v1/employees?manager_id={manager['id']}", headers=hr_headers).json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == report["id"]


def test_search_and_filter_employees(client: TestClient, hr_headers: dict[str, str]) -> None:
    _create_employee(
        client, hr_headers, number="E-SEARCH1", email="findme@example.com", first_name="Zora"
    )
    _create_employee(client, hr_headers, number="E-SEARCH2", email="other2@example.com")

    response = client.get("/api/v1/employees?search=Zora", headers=hr_headers)
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["first_name"] == "Zora"


def test_terminate_employee_via_patch(client: TestClient, hr_headers: dict[str, str]) -> None:
    created = _create_employee(client, hr_headers, number="E-TERM", email="term@example.com")

    response = client.patch(
        f"/api/v1/employees/{created['id']}",
        json={"employment_status": "terminated", "termination_date": "2024-06-01"},
        headers=hr_headers,
    )
    assert response.status_code == 200
    assert response.json()["employment_status"] == "terminated"


def test_delete_employee(client: TestClient, hr_headers: dict[str, str]) -> None:
    created = _create_employee(client, hr_headers, number="E-DEL", email="del@example.com")

    deleted = client.delete(f"/api/v1/employees/{created['id']}", headers=hr_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/employees/{created['id']}", headers=hr_headers).status_code == 404
