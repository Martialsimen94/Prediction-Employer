"""Integration tests for registration, login, refresh, and RBAC.

Runs against a real Postgres (see conftest.db_session), each test wrapped
in a rolled-back transaction. The FastAPI app's own DB dependency is
overridden to reuse that same transactional session so API calls and
direct model assertions see the same uncommitted state.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_token
from app.main import app
from app.models.auth import Role
from app.services.auth_service import AuthService


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_register_then_login(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register", json={"email": "ada@example.com", "password": "correct-horse-1"}
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == "ada@example.com"
    assert body["roles"] == ["employee"]

    login_response = client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": "correct-horse-1"}
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]


def test_register_duplicate_email_is_rejected(client: TestClient) -> None:
    payload = {"email": "dup@example.com", "password": "correct-horse-1"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409


def test_login_with_wrong_password_is_rejected(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register", json={"email": "wrong@example.com", "password": "correct-horse-1"}
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "wrong@example.com", "password": "not-the-password"}
    )
    assert response.status_code == 401


def test_me_requires_a_valid_access_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
        ).status_code
        == 401
    )


def test_me_returns_current_user_for_valid_token(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register", json={"email": "me@example.com", "password": "correct-horse-1"}
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": "me@example.com", "password": "correct-horse-1"}
    )
    access_token = login.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_refresh_token_issues_a_new_access_token(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "correct-horse-1"},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": "refresh@example.com", "password": "correct-horse-1"}
    )
    refresh_token = login.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_access_token_cannot_be_used_as_a_refresh_token(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register", json={"email": "reuse@example.com", "password": "correct-horse-1"}
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": "reuse@example.com", "password": "correct-horse-1"}
    )
    access_token = login.json()["access_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_expired_access_token_is_rejected(client: TestClient, db_session: Session) -> None:
    service = AuthService(db_session)
    user = service.register(email="expired@example.com", password="correct-horse-1")
    db_session.flush()

    with patch("app.core.security.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime.now(UTC) - timedelta(minutes=60)
        expired_token = create_token(str(user.id), "access")

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_seeded_hr_role_has_expected_permissions(db_session: Session) -> None:
    hr_role = db_session.scalar(select(Role).where(Role.name == "hr"))
    assert hr_role is not None
    codes = {permission.code for permission in hr_role.permissions}
    assert codes == {
        "employees:read",
        "employees:write",
        "salaries:read",
        "salaries:write",
        "predictions:read",
        "audit:read",
    }


def test_user_registered_with_a_non_default_role_reports_it_via_me(
    client: TestClient, db_session: Session
) -> None:
    # Role assignment beyond the "employee" default is an admin action with
    # no endpoint yet (Module 4 adds user management); exercised directly
    # against AuthService here.
    service = AuthService(db_session)
    user = service.register(
        email="hasrole@example.com", password="correct-horse-1", default_role="hr"
    )
    assert [role.name for role in user.roles] == ["hr"]
    token = create_token(str(user.id), "access")

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["roles"] == ["hr"]
