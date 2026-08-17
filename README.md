# AI Employee Retention Platform

An end-to-end platform that predicts employee attrition risk, explains each prediction (SHAP/LIME), and recommends concrete retention actions — built with production-grade practices (Clean Architecture, Repository/Service layers, typed code, tested pipelines, MLOps).

> **Status:** under active development, built module by module. See [Roadmap](#roadmap) for progress.

## What this project is

HR teams typically learn an employee is at flight risk only after they resign. This platform turns HR data (compensation, performance, promotions, absences, training, tenure, engagement signals) into:

1. **A calibrated attrition-risk score** per employee, produced by the best of several competing ML models (Random Forest, XGBoost, LightGBM, CatBoost, Logistic Regression, Neural Network), auto-selected via cross-validated benchmarking and Optuna-tuned hyperparameters.
2. **A plain-language explanation** of *why* — global and per-prediction feature attribution via SHAP and LIME.
3. **A recommended action** — salary review, training, promotion, internal mobility, coaching, team change, workload reduction, mentoring — mapped from the specific risk factors driving each prediction.
4. **Role-specific dashboards** (HR, Executive, Manager, Data Scientist) and a full REST API secured with JWT/RBAC.

## Tech stack

| Layer | Technologies |
|---|---|
| Backend / API | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Data & Cache | PostgreSQL 16, Redis 7, Celery |
| Machine Learning | scikit-learn, XGBoost, LightGBM, CatBoost, Optuna, SHAP, LIME |
| MLOps | MLflow (tracking + model registry), drift monitoring, automated retraining |
| Visualization | Plotly, Dash, Streamlit |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Infra | Docker, Docker Compose, GitHub Actions |
| Testing | pytest, pytest-cov, httpx |

## Architecture

Clean Architecture with a Repository Pattern + Service Layer on the backend (`backend/app/{repositories,services,api}`), a decoupled ML pipeline (`ml/{etl,training,explainability,monitoring}`) tracked in MLflow, and independent dashboard/frontend clients consuming the same versioned REST API. See [`docs/architecture`](docs/architecture) for diagrams (system architecture, ERD, UML) as they are added.

```
backend/    FastAPI application (API, domain, repositories, services, ML inference)
ml/         Data engineering, model training/comparison, explainability, drift monitoring
dashboards/ Streamlit & Dash apps (HR / Executive / Manager / Data Scientist views)
frontend/   React + TypeScript + Tailwind SPA
db/         SQL views, triggers, stored procedures, schema diagrams
docker/     Docker Compose stack definitions
docs/       Architecture, technical and user documentation
```

## Getting started (development)

Prerequisites: [Poetry](https://python-poetry.org/) 2.x, Python 3.12, [pnpm](https://pnpm.io/), Docker (for Postgres/Redis and, later, the full stack).

```bash
# 1. Install Python dependencies (base + dev tooling)
poetry install

# 2. Copy environment template and adjust as needed
cp .env.example .env

# 3. Start Postgres + Redis
docker compose -f docker/docker-compose.yml up -d

# 4. Run the test suite
poetry run pytest

# 5. Lint & type-check
poetry run ruff check .
poetry run mypy backend/app ml
```

> **Docker Desktop on macOS:** `brew install --cask docker` links a helper binary via `sudo`, which requires an interactive password prompt — run it yourself in a real terminal, then launch `Docker.app` once to finish setup. Until Docker is available, Postgres/Redis can run locally instead: `brew install postgresql@16 redis && brew services start postgresql@16 redis`, then create a dedicated role/database (`CREATE ROLE retention_app LOGIN PASSWORD '...'; CREATE DATABASE retention_platform OWNER retention_app;`) and point `.env` at it. Note: the Homebrew `redis` formula 8.x ships a `redis.conf` with broken relative `loadmodule` paths (Redis Stack modules that aren't actually bundled) — comment out the `loadmodule ./modules/...` lines under `/opt/homebrew/etc/redis.conf` if the service fails to start.

Optional dependency groups are installed on demand as later modules need them, e.g.:

```bash
poetry install --with api      # FastAPI, Celery, auth
poetry install --with ml       # pandas, XGBoost, SHAP, MLflow...
poetry install --with dashboards
```

## Database

The schema (21 tables — employees, departments, salaries, performance reviews,
promotions, absences, trainings, skills, auth/RBAC, ML predictions/recommendations,
notifications, audit log, MLOps model registry & drift reports) is fully normalized,
constrained (CHECK/UNIQUE/FK with appropriate `ON DELETE` behavior) and indexed.
Reporting views, audit/`updated_at` triggers and a turnover-rate stored function live
in [`db/sql`](db/sql) and are applied by the second Alembic migration.

```bash
cd backend
poetry run alembic upgrade head      # apply all migrations
poetry run alembic downgrade base    # roll back everything (dev/test only)
poetry run alembic revision --autogenerate -m "..."   # after changing models
```

## Roadmap

The platform is built and tested module by module (see the project plan for full detail):

- [x] **1. Foundations** — monorepo structure, Poetry, pnpm, pre-commit, Docker Compose skeleton, CI skeleton
- [x] **2. Database schema & Alembic migrations** — 21 normalized tables, constraints/indexes, `db/sql` views/triggers/stored function
- [ ] 3. Authentication & RBAC
- [ ] 4. Core HR domain API (employees, departments, managers, salaries, reviews, promotions, absences, training)
- [ ] 5. Notifications & audit log
- [ ] 6. Data engineering — dataset generation & ETL pipeline
- [ ] 7. ML training, benchmarking & MLflow tracking
- [ ] 8. Explainability (SHAP/LIME) & recommendation engine
- [ ] 9. ML inference API
- [ ] 10. MLOps — drift detection & automated retraining
- [ ] 11. Dashboards (Streamlit/Dash)
- [ ] 12. Frontend (React/TypeScript/Tailwind)
- [ ] 13. Full Docker Compose stack & complete CI/CD
- [ ] 14. Final documentation (architecture diagrams, technical & user guides)

## License

MIT
