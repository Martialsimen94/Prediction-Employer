# A small, purpose-built image for the tracking server rather than the
# third-party `ghcr.io/mlflow/mlflow` image: pinning the exact mlflow
# version the client library resolves to (see poetry.lock) avoids any
# server/client API drift, and building on the same python:3.12-slim base
# used everywhere else in this repo means the tools available here (pip,
# curl) are known rather than guessed.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Keep this version in sync with the `mlflow` entry in ../../poetry.lock.
RUN pip install "mlflow==2.22.5"

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:5000/health || exit 1

ENTRYPOINT ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
