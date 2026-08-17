"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine
from app.core.redis import get_redis_client
from app.schemas.health import HealthStatus

settings = get_settings()

app = FastAPI(title=settings.project_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _database_is_reachable() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - health check must never raise
        return False
    return True


def _redis_is_reachable() -> bool:
    try:
        return bool(get_redis_client().ping())
    except Exception:  # noqa: BLE001 - health check must never raise
        return False


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"name": settings.project_name, "status": "running"}


@app.get("/health", response_model=HealthStatus, tags=["meta"])
def health() -> HealthStatus:
    database_ok = _database_is_reachable()
    redis_ok = _redis_is_reachable()
    return HealthStatus(
        status="ok" if database_ok and redis_ok else "degraded",
        database=database_ok,
        redis=redis_ok,
    )
