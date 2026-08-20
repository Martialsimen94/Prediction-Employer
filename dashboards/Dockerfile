# Shared image for both dashboard apps (streamlit_app, dash_app) -- same
# poetry group, same code tree. docker-compose.yml overrides `command:` per
# service to pick which one actually runs. Built from the repo root; only
# needs `dashboards/` itself (the REST client in dashboards/common/ talks
# to the backend over HTTP, never imports app.* or ml.* directly).

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app

RUN pip install "poetry==2.4.1"

# README.md required by poetry even though package-mode = false skips
# building the local package -- see backend/Dockerfile's comment.
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --with dashboards --without dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/dashboards"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY dashboards/ dashboards/

EXPOSE 8501 8050

CMD ["streamlit", "run", "dashboards/streamlit_app/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
