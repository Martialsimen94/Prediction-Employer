"""FastAPI application entrypoint."""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.v1.absences import router as absences_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.departments import router as departments_router
from app.api.v1.employees import router as employees_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.performance_reviews import router as performance_reviews_router
from app.api.v1.predictions import (
    employee_predictions_router,
    predictions_router,
    recommendations_router,
)
from app.api.v1.promotions import router as promotions_router
from app.api.v1.salaries import router as salaries_router
from app.api.v1.trainings import catalog_router as trainings_catalog_router
from app.api.v1.trainings import enrollment_router as trainings_enrollment_router
from app.core.config import get_settings
from app.core.db import engine
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
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


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)}
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Fallback for constraint violations not pre-validated by a service
    (e.g. a race on a unique constraint)."""
    logger.warning("integrity_error", path=request.url.path, error=str(exc.orig))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": "Conflicting or invalid data"}
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
app.include_router(departments_router, prefix=settings.api_v1_prefix)
app.include_router(employees_router, prefix=settings.api_v1_prefix)
app.include_router(salaries_router, prefix=settings.api_v1_prefix)
app.include_router(performance_reviews_router, prefix=settings.api_v1_prefix)
app.include_router(promotions_router, prefix=settings.api_v1_prefix)
app.include_router(employee_predictions_router, prefix=settings.api_v1_prefix)
app.include_router(predictions_router, prefix=settings.api_v1_prefix)
app.include_router(recommendations_router, prefix=settings.api_v1_prefix)
app.include_router(absences_router, prefix=settings.api_v1_prefix)
app.include_router(trainings_catalog_router, prefix=settings.api_v1_prefix)
app.include_router(trainings_enrollment_router, prefix=settings.api_v1_prefix)
app.include_router(notifications_router, prefix=settings.api_v1_prefix)
app.include_router(audit_router, prefix=settings.api_v1_prefix)


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
