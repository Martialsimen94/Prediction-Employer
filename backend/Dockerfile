# Backend API + Celery worker/beat image. Built from the repo root (see
# docker/docker-compose.yml's `context: ..`), because it needs both
# `backend/` and `ml/` -- the API imports ml.inference/ml.monitoring
# directly for predictions and drift checks (Modules 9-10), it isn't a thin
# REST-only layer -- plus `db/sql/*.sql`, which Alembic reads and applies
# at migration time (see backend/alembic/versions/977e01171c99_...).

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app

RUN pip install "poetry==2.4.1"

# README.md is required even though package-mode = false skips building
# the local package: poetry still validates pyproject.toml's `readme`
# field points at a real file (fails install otherwise, confirmed with
# `poetry check` against a copy missing it).
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --with api,ml --without dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/backend:/app"

# lightgbm/catboost need libgomp1 (OpenMP) at *import* time, not just build
# time -- the slim base doesn't ship it, so `import lightgbm` segfaults
# without this even though the wheel itself installed fine.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY backend/ backend/
COPY ml/ ml/
COPY db/ db/

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
