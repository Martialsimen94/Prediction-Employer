"""Smoke tests for the FastAPI application entrypoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_running_status() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert "name" in body


def test_health_reports_database_and_redis() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert isinstance(body["database"], bool)
    assert isinstance(body["redis"], bool)
