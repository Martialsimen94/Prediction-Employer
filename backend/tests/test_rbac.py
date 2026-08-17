"""Unit tests for the require_permission() RBAC dependency, in isolation
from the DB and HTTP layers."""

import pytest
from fastapi import HTTPException

from app.api.deps import require_permission
from app.models.auth import Permission, Role, User


def _user_with_permissions(*codes: str) -> User:
    role = Role(name="test-role")
    role.permissions = [Permission(code=code) for code in codes]
    user = User(email="u@example.com", hashed_password="x", is_active=True)
    user.roles = [role]
    return user


def test_require_permission_denies_a_user_without_the_code() -> None:
    dependency = require_permission("employees:read")
    user = _user_with_permissions("salaries:read")

    with pytest.raises(HTTPException) as exc_info:
        dependency(user)

    assert exc_info.value.status_code == 403


def test_require_permission_allows_a_user_with_the_code() -> None:
    dependency = require_permission("employees:read")
    user = _user_with_permissions("salaries:read", "employees:read")

    assert dependency(user) is user


def test_require_permission_denies_a_user_with_no_roles() -> None:
    dependency = require_permission("employees:read")
    user = User(email="norole@example.com", hashed_password="x", is_active=True)

    with pytest.raises(HTTPException) as exc_info:
        dependency(user)

    assert exc_info.value.status_code == 403
