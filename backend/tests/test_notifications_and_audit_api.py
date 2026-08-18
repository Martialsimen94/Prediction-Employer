"""Integration tests for notifications and the audit log API.

Celery's `.delay()` is monkeypatched to a synchronous no-op in these tests
so they don't depend on a running worker/broker — dispatch behavior itself
is covered by the live worker smoke test run separately.
"""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_token
from app.main import app
from app.models.auth import User
from app.services.auth_service import AuthService
from tests.auth_test_helpers import auth_header_for_role


@pytest.fixture(autouse=True)
def _no_real_celery_dispatch() -> Generator[None, None, None]:
    with patch("app.services.notification_service.deliver_notification_task.delay"):
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
    return auth_header_for_role(db_session, role="hr", email="hr-notif@example.com")


def _create_employee_with_user(
    client: TestClient, hr_headers: dict[str, str], db_session: Session
) -> tuple[int, dict[str, str]]:
    """An employee whose email matches a registered user account, so
    promoting them triggers a notification to that account."""
    user = AuthService(db_session).register(
        email="promotable@example.com", password="correct-horse-1", default_role="employee"
    )
    db_session.flush()
    token = create_token(str(user.id), "access")

    created = client.post(
        "/api/v1/employees",
        json={
            "employee_number": "E-NOTIF",
            "first_name": "Alan",
            "last_name": "Turing",
            "email": "promotable@example.com",
            "hire_date": "2020-01-01",
            "job_title": "Engineer",
        },
        headers=hr_headers,
    )
    assert created.status_code == 201
    employee_id = created.json()["id"]

    # Link the user account to the employee record directly (Module 4 has
    # no endpoint for this yet — it's an account-provisioning concern).
    db_user = db_session.get(User, user.id)
    assert db_user is not None
    db_user.employee_id = employee_id
    db_session.flush()

    return employee_id, {"Authorization": f"Bearer {token}"}


def test_promotion_creates_a_notification_for_the_linked_user(
    client: TestClient, hr_headers: dict[str, str], db_session: Session
) -> None:
    employee_id, employee_headers = _create_employee_with_user(client, hr_headers, db_session)

    promoted = client.post(
        f"/api/v1/employees/{employee_id}/promotions",
        json={
            "previous_job_title": "Engineer",
            "new_job_title": "Senior Engineer",
            "promotion_date": "2024-01-01",
        },
        headers=hr_headers,
    )
    assert promoted.status_code == 201

    notifications = client.get("/api/v1/notifications", headers=employee_headers)
    assert notifications.status_code == 200
    body = notifications.json()
    assert body["total"] == 1
    assert body["items"][0]["notification_type"] == "promotion"
    assert body["items"][0]["is_read"] is False


def test_mark_notification_read(
    client: TestClient, hr_headers: dict[str, str], db_session: Session
) -> None:
    employee_id, employee_headers = _create_employee_with_user(client, hr_headers, db_session)
    client.post(
        f"/api/v1/employees/{employee_id}/promotions",
        json={
            "previous_job_title": "Engineer",
            "new_job_title": "Staff Engineer",
            "promotion_date": "2024-01-01",
        },
        headers=hr_headers,
    )
    notification_id = client.get("/api/v1/notifications", headers=employee_headers).json()["items"][
        0
    ]["id"]

    response = client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=employee_headers
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True

    unread = client.get("/api/v1/notifications?unread_only=true", headers=employee_headers).json()
    assert unread["total"] == 0


def test_a_user_cannot_read_another_users_notification(
    client: TestClient, hr_headers: dict[str, str], db_session: Session
) -> None:
    employee_id, _owner_headers = _create_employee_with_user(client, hr_headers, db_session)
    client.post(
        f"/api/v1/employees/{employee_id}/promotions",
        json={
            "previous_job_title": "Engineer",
            "new_job_title": "Staff Engineer",
            "promotion_date": "2024-01-01",
        },
        headers=hr_headers,
    )
    notification_id = client.get("/api/v1/notifications", headers=_owner_headers).json()["items"][
        0
    ]["id"]

    outsider = auth_header_for_role(db_session, role="employee", email="outsider@example.com")
    response = client.get(f"/api/v1/notifications/{notification_id}", headers=outsider)
    assert response.status_code == 404


def test_audit_log_records_salary_changes(client: TestClient, hr_headers: dict[str, str]) -> None:
    employee = client.post(
        "/api/v1/employees",
        json={
            "employee_number": "E-AUDIT-API",
            "first_name": "Rear",
            "last_name": "Admiral",
            "email": "audit-api@example.com",
            "hire_date": "2020-01-01",
            "job_title": "Engineer",
        },
        headers=hr_headers,
    ).json()

    salary = client.post(
        f"/api/v1/employees/{employee['id']}/salaries",
        json={"amount": "80000", "effective_date": "2020-01-01", "reason": "initial"},
        headers=hr_headers,
    ).json()

    response = client.get(
        f"/api/v1/audit-log?table_name=salaries&record_id={salary['id']}",
        headers=hr_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == "INSERT"
    assert body["items"][0]["new_data"]["amount"] == 80000.0


def test_audit_log_requires_permission(client: TestClient, db_session: Session) -> None:
    plain_headers = auth_header_for_role(
        db_session, role="employee", email="plain-audit@example.com"
    )
    response = client.get("/api/v1/audit-log", headers=plain_headers)
    assert response.status_code == 403
