"""Integration tests for salary, performance review, promotion, absence and
training endpoints — all nested under an employee (except the training
catalog itself)."""

import uuid
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
    return auth_header_for_role(db_session, role="hr", email="hr-sub@example.com")


@pytest.fixture
def employee_id(client: TestClient, hr_headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/employees",
        json={
            "employee_number": "E-SUB1",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada-sub@example.com",
            "hire_date": "2020-01-15",
            "job_title": "Staff Engineer",
        },
        headers=hr_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


# --- Salaries -----------------------------------------------------------


def test_salary_create_and_list(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    created = client.post(
        f"/api/v1/employees/{employee_id}/salaries",
        json={"amount": "95000.00", "effective_date": "2020-01-15", "reason": "initial"},
        headers=hr_headers,
    )
    assert created.status_code == 201
    assert created.json()["end_date"] is None

    listed = client.get(f"/api/v1/employees/{employee_id}/salaries", headers=hr_headers)
    assert listed.json()["total"] == 1


def test_new_salary_closes_the_previous_open_row(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    client.post(
        f"/api/v1/employees/{employee_id}/salaries",
        json={"amount": "95000.00", "effective_date": "2020-01-15", "reason": "initial"},
        headers=hr_headers,
    )
    second = client.post(
        f"/api/v1/employees/{employee_id}/salaries",
        json={"amount": "105000.00", "effective_date": "2021-01-15", "reason": "raise"},
        headers=hr_headers,
    )
    assert second.status_code == 201

    listing = client.get(f"/api/v1/employees/{employee_id}/salaries", headers=hr_headers).json()
    assert listing["total"] == 2
    closed = next(row for row in listing["items"] if row["reason"] == "initial")
    assert closed["end_date"] == "2021-01-14"


def test_salary_for_missing_employee_is_404(client: TestClient, hr_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/employees/999999/salaries",
        json={"amount": "1000", "effective_date": "2024-01-01", "reason": "initial"},
        headers=hr_headers,
    )
    assert response.status_code == 404


def test_salary_amount_must_be_positive(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    response = client.post(
        f"/api/v1/employees/{employee_id}/salaries",
        json={"amount": "-1", "effective_date": "2024-01-01", "reason": "initial"},
        headers=hr_headers,
    )
    assert response.status_code == 422


# --- Performance reviews -------------------------------------------------


def test_performance_review_create_and_update(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    created = client.post(
        f"/api/v1/employees/{employee_id}/performance-reviews",
        json={"review_date": "2024-01-01", "review_period": "2023-H2", "score": "4.5"},
        headers=hr_headers,
    )
    assert created.status_code == 201
    review_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/employees/{employee_id}/performance-reviews/{review_id}",
        json={"comments": "Exceeded expectations"},
        headers=hr_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["comments"] == "Exceeded expectations"


def test_performance_review_score_out_of_range_is_rejected(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    response = client.post(
        f"/api/v1/employees/{employee_id}/performance-reviews",
        json={"review_date": "2024-01-01", "review_period": "2023-H2", "score": "9.9"},
        headers=hr_headers,
    )
    assert response.status_code == 422


# --- Promotions -----------------------------------------------------------


def test_promotion_updates_employee_job_title(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    promoted = client.post(
        f"/api/v1/employees/{employee_id}/promotions",
        json={
            "previous_job_title": "Staff Engineer",
            "new_job_title": "Principal Engineer",
            "promotion_date": "2024-03-01",
        },
        headers=hr_headers,
    )
    assert promoted.status_code == 201

    employee = client.get(f"/api/v1/employees/{employee_id}", headers=hr_headers).json()
    assert employee["job_title"] == "Principal Engineer"


# --- Absences ---------------------------------------------------------


def test_absence_create_approve_and_delete(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    created = client.post(
        f"/api/v1/employees/{employee_id}/absences",
        json={"absence_type": "vacation", "start_date": "2024-07-01", "end_date": "2024-07-10"},
        headers=hr_headers,
    )
    assert created.status_code == 201
    assert created.json()["approved"] is False
    absence_id = created.json()["id"]

    approved = client.patch(
        f"/api/v1/employees/{employee_id}/absences/{absence_id}",
        json={"approved": True},
        headers=hr_headers,
    )
    assert approved.json()["approved"] is True

    deleted = client.delete(
        f"/api/v1/employees/{employee_id}/absences/{absence_id}", headers=hr_headers
    )
    assert deleted.status_code == 204


def test_absence_end_before_start_is_rejected(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    response = client.post(
        f"/api/v1/employees/{employee_id}/absences",
        json={"absence_type": "sick", "start_date": "2024-07-10", "end_date": "2024-07-01"},
        headers=hr_headers,
    )
    assert response.status_code == 422


# --- Trainings ----------------------------------------------------------


def test_training_catalog_crud(client: TestClient, hr_headers: dict[str, str]) -> None:
    # A name unlikely to collide with the fixed course catalog the ETL
    # pipeline (Module 6) may have already seeded into the dev database.
    unique_name = f"Advanced SQL Tuning {uuid.uuid4().hex[:8]}"

    created = client.post(
        "/api/v1/trainings",
        json={"name": unique_name, "provider": "Internal", "duration_hours": 8},
        headers=hr_headers,
    )
    assert created.status_code == 201
    training_id = created.json()["id"]

    duplicate = client.post(
        "/api/v1/trainings",
        json={"name": unique_name, "duration_hours": 4},
        headers=hr_headers,
    )
    assert duplicate.status_code == 409

    listed = client.get(f"/api/v1/trainings?search={unique_name}", headers=hr_headers)
    assert listed.json()["total"] == 1

    updated = client.patch(
        f"/api/v1/trainings/{training_id}", json={"duration_hours": 10}, headers=hr_headers
    )
    assert updated.json()["duration_hours"] == 10

    deleted = client.delete(f"/api/v1/trainings/{training_id}", headers=hr_headers)
    assert deleted.status_code == 204


def test_employee_training_enrollment_lifecycle(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    training = client.post(
        "/api/v1/trainings",
        json={"name": "Leadership 101", "duration_hours": 6},
        headers=hr_headers,
    ).json()

    enrolled = client.post(
        f"/api/v1/employees/{employee_id}/trainings",
        json={"training_id": training["id"], "start_date": "2024-05-01"},
        headers=hr_headers,
    )
    assert enrolled.status_code == 201
    assert enrolled.json()["status"] == "enrolled"
    enrollment_id = enrolled.json()["id"]

    completed = client.patch(
        f"/api/v1/employees/{employee_id}/trainings/{enrollment_id}",
        json={"status": "completed", "completion_date": "2024-05-08", "score": "95"},
        headers=hr_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["score"] == "95"


def test_enrollment_requires_an_existing_training(
    client: TestClient, hr_headers: dict[str, str], employee_id: int
) -> None:
    response = client.post(
        f"/api/v1/employees/{employee_id}/trainings",
        json={"training_id": 999999, "start_date": "2024-05-01"},
        headers=hr_headers,
    )
    assert response.status_code == 404
