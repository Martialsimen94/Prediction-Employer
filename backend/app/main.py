"""FastAPI application entrypoint."""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.v1.auth import router as auth_router
from app.core.config import get_settings
from app.core.db import engine
from app.core.limiter import limiter
from app.core.redis import get_redis_client
from app.schemas.health import HealthStatus

logger = structlog.get_logger()

settings = get_settings()

app = FastAPI(title=settings.project_name, version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Centralized fallback: log the real error, never leak internals to the client."""
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.include_router(auth_router, prefix=settings.api_v1_prefix)


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
