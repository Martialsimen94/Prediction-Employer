"""Thin REST client for the backend API. Every dashboard view reads (and
occasionally writes — e.g. triggering a drift check) through this API,
never a direct DB connection: dashboards are meant to be "independent
[...] clients consuming the same versioned REST API" as everything else
(see the top-level README's Architecture section)."""

import contextlib
import os
from dataclasses import dataclass, field
from typing import Any

import requests

DEFAULT_BASE_URL = os.environ.get("RETENTION_API_BASE_URL", "http://localhost:8000/api/v1")


class ApiError(RuntimeError):
    """Raised for any non-2xx response, carrying the API's own `detail`
    message so callers can show it as-is rather than a generic failure."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


@dataclass
class ApiSession:
    """One logged-in session: the access token plus the `/auth/me` payload
    (roles, employee_id) dashboards use to decide what to render."""

    base_url: str
    access_token: str
    user: dict[str, Any] = field(default_factory=dict)

    @property
    def roles(self) -> list[str]:
        return list(self.user.get("roles", []))

    @property
    def employee_id(self) -> int | None:
        employee_id = self.user.get("employee_id")
        return int(employee_id) if employee_id is not None else None

    def has_role(self, *names: str) -> bool:
        return bool(set(self.roles) & set(names))


def _raise_for_status(response: requests.Response) -> None:
    if response.ok:
        return
    detail = response.text
    with contextlib.suppress(ValueError):
        detail = response.json().get("detail", detail)
    raise ApiError(response.status_code, str(detail))


def login(email: str, password: str, *, base_url: str = DEFAULT_BASE_URL) -> ApiSession:
    response = requests.post(
        f"{base_url}/auth/login", json={"email": email, "password": password}, timeout=10
    )
    _raise_for_status(response)
    access_token = response.json()["access_token"]

    session = ApiSession(base_url=base_url, access_token=access_token)
    session.user = get(session, "/auth/me")
    return session


def _headers(session: ApiSession) -> dict[str, str]:
    return {"Authorization": f"Bearer {session.access_token}"}


def get(session: ApiSession, path: str, **params: Any) -> Any:
    response = requests.get(
        f"{session.base_url}{path}",
        headers=_headers(session),
        params={key: value for key, value in params.items() if value is not None},
        timeout=10,
    )
    _raise_for_status(response)
    return response.json()


def post(session: ApiSession, path: str, json: dict[str, Any] | None = None) -> Any:
    response = requests.post(
        f"{session.base_url}{path}", headers=_headers(session), json=json, timeout=30
    )
    _raise_for_status(response)
    return response.json() if response.content else None


def patch(session: ApiSession, path: str, json: dict[str, Any] | None = None) -> Any:
    response = requests.patch(
        f"{session.base_url}{path}", headers=_headers(session), json=json, timeout=10
    )
    _raise_for_status(response)
    return response.json()
