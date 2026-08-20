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
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query |
| Infra | Docker, Docker Compose, GitHub Actions |
| Testing | pytest, pytest-cov, httpx, Vitest, Testing Library |

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

Prerequisites: [Poetry](https://python-poetry.org/) 2.x, Python 3.12, [pnpm](https://pnpm.io/), Docker (for Postgres/Redis locally, or the [full stack](#full-stack-docker-compose)).

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

The frontend is a separate pnpm workspace (see [Frontend](#frontend) below) — `pnpm install` from the repo root sets it up.

## Database

The schema (22 tables — employees, departments, salaries, performance reviews,
promotions, absences, trainings, skills, auth/RBAC, ML predictions/recommendations,
an employee feature snapshot store, notifications, audit log, MLOps model registry &
drift reports) is fully normalized,
constrained (CHECK/UNIQUE/FK with appropriate `ON DELETE` behavior) and indexed.
Reporting views, audit/`updated_at` triggers and a turnover-rate stored function live
in [`db/sql`](db/sql) and are applied by the second Alembic migration.

```bash
cd backend
poetry run alembic upgrade head      # apply all migrations
poetry run alembic downgrade base    # roll back everything (dev/test only)
poetry run alembic revision --autogenerate -m "..."   # after changing models
```

## Data & ETL

The seed dataset is the public [IBM HR Analytics Employee Attrition &
Performance](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset)
dataset (1,470 real fictional-but-realistic employees, 35 features) — not committed to
the repo (`ml/data/raw/` is gitignored; a sha256 checksum guards the fetch):

```bash
poetry run python ml/etl/download_seed_dataset.py
```

The ETL pipeline (`ml/etl/`) validates it with Pandera, cleans it (missing
values, IQR outlier flagging), bootstrap+jitter-augments it up to an
"enterprise" row count while preserving the real data's joint statistics
(a resampled real row, not independently resampled columns — correlations
like OverTime+low JobSatisfaction -> Attrition survive), maps it onto our
domain tables (with a JobLevel-based manager hierarchy per department),
synthesizes plausible absences/training enrollments the source data doesn't
contain, snapshots each employee's raw model-input feature vector into
`employee_feature_snapshots` (the offline feature store the inference API
below reads from), and bulk-loads everything into Postgres via SQLAlchemy
Core (INSERT...RETURNING, not row-by-row ORM — ~5,000 employees plus
~20,000 related rows load in about 2 seconds):

```bash
PYTHONPATH=backend poetry run python -m ml.etl.pipeline --target-rows 5000
# --dry-run runs every stage except the DB load, to sanity-check counts/timing
```

A reusable sklearn `ColumnTransformer` (`ml/etl/features.py`, encoding +
scaling) is shared with the training pipeline below so both agree on
exactly which columns feed the model.

## Machine Learning

Six candidate models (Logistic Regression, Random Forest, XGBoost, LightGBM,
CatBoost, a small MLP) are each Optuna-tuned, cross-validated, evaluated
(accuracy/precision/recall/F1/ROC AUC, confusion matrix, calibration curve,
learning curve, feature importance where applicable) and tracked in MLflow;
the best one (by test ROC AUC) is registered in the MLflow Model Registry
under a `staging` alias:

```bash
PYTHONPATH=backend poetry run python -m ml.training.train --target-rows 5000 --n-trials 12
# --quick runs a small/fast version first, to sanity-check the whole pipeline
poetry run mlflow ui --backend-store-uri sqlite:///mlruns.db   # browse runs
```

**A methodology note worth keeping in mind when extending this pipeline:**
because synthetic rows are close relatives of the real row they were
bootstrapped from (see [Data & ETL](#data--etl) above), a plain stratified
train/test split let a row and its near-duplicate land on opposite sides of
the split in early runs — inflating ROC AUC to ~0.99 by letting models
partly recognize near-duplicates rather than learn the real pattern. Every
synthetic row now carries a `lineage_id` back to the real employee it was
resampled from, and both the train/test split and every cross-validation
fold use `StratifiedGroupKFold` so a lineage never straddles a split. The
corrected scores (~0.78-0.80 ROC AUC) line up with published benchmarks
for this real dataset. See `ml/notebooks/01_eda_and_model_comparison.ipynb`
for the full writeup, EDA, and model comparison charts.

## Explainability

Every prediction is paired with SHAP and LIME attributions and a short list
of concrete recommendations, in `ml/explainability/`:

- `ShapExplainer` — exact TreeExplainer attribution for the tree-ensemble
  models (Random Forest, XGBoost, LightGBM, CatBoost), a model-agnostic
  `shap.Explainer` fallback for Logistic Regression / the MLP; both are
  computed in the pipeline's transformed feature space and aggregated back
  onto the original employee columns.
- `LimeExplainer` — a local linear surrogate fit around each instance, as an
  independent cross-check against SHAP's Shapley-value attribution.
- `recommendations.py` — maps the SHAP-driven risk factors to actionable HR
  levers (salary review, training, promotion, internal mobility, coaching,
  team change, workload reduction, mentoring), one recommendation per action
  type, prioritized by risk level. `Gender`/`MaritalStatus` are deliberately
  excluded from the actionable-feature map: an HR platform must never
  justify an intervention by a protected/demographic attribute.
- `ExplanationEngine` ties the three together into one
  `PredictionExplanation` per employee, shaped to match the
  `attrition_predictions` / `recommendations` tables so Module 9's inference
  API can persist it directly.

## ML Inference API

`ml/inference/` bridges the trained model (Module 7) and the explanation
engine (Module 8) into the live backend:

- `model_loader.py` loads the pipeline currently under the MLflow registry's
  `staging` alias and lazily mirrors it into the `ml_model_registry` table
  (the FK every persisted prediction points at), so promoting a new model in
  MLflow is all it takes for the next prediction to use it.
- `features.py` reconstructs a model-ready row (or background sample) from
  `employee_feature_snapshots` JSON blobs, coercing values back to the
  dtypes the training pipeline's `ColumnTransformer` expects.

`PredictionService` (`backend/app/services/prediction_service.py`) ties
these into the REST API: scoring an employee fits (or reuses a
process-cached) `ExplanationEngine`, then persists the resulting risk score,
SHAP attribution and recommendations in one call.

| Endpoint | Permission | Description |
|---|---|---|
| `POST /employees/{id}/predictions` | `predictions:write` | Score the employee from their latest feature snapshot; persists the prediction + recommendations |
| `GET /employees/{id}/predictions` | `predictions:read` | Paginated prediction history for the employee |
| `GET /predictions/{id}` | `predictions:read` | A single prediction with its recommendations |
| `PATCH /recommendations/{id}` | `predictions:write` | Update a recommendation's status (`pending`/`in_progress`/`completed`/`dismissed`) |

```bash
PYTHONPATH=. poetry run uvicorn app.main:app --app-dir backend --reload
```

## MLOps: drift detection & retraining

`ml/monitoring/` compares two `employee_feature_snapshots` periods — the
oldest ETL batch on record as the reference distribution, the most recent
one as current — one check per feature:

- `drift.py` — a Kolmogorov-Smirnov two-sample test for numeric features,
  a Population Stability Index (PSI) for categorical ones; each yields a
  `drift_score` and a `drift_detected` flag against a conventional
  threshold (KS p < 0.05, PSI > 0.25).
- `reports.py` — persists one `data_drift_reports` row per feature per
  check.
- `retrain.py` — if enough features have drifted (3 by default), reruns
  the full training pipeline (Module 7) and promotes the result to a new
  `production` MLflow alias — but only if it beats whatever's currently
  serving (`production` if anything's ever been promoted, `staging`
  otherwise), so a bad retrain can never silently regress predictions.
  The inference API (Module 9) prefers `production` and falls back to
  `staging`.

A Celery Beat schedule runs the check nightly (`app/core/celery_app.py`);
`POST /drift-reports/check` triggers it on demand:

| Endpoint | Permission | Description |
|---|---|---|
| `GET /drift-reports` | `predictions:read` | Paginated drift reports, filterable by `feature_name` / `drift_detected` |
| `POST /drift-reports/check` | `predictions:write` | Enqueue an async drift check (and a possible retrain + promotion) |

```bash
cd backend
PYTHONPATH=..:. poetry run celery -A app.core.celery_app worker --beat --loglevel=info
```

## Dashboards

Two clients, four role-specific views, both reading and occasionally writing
through the REST API above — never a direct database connection, so they're
subject to the exact same RBAC as everyone else:

- **`dashboards/streamlit_app/`** — HR and Manager. HR sees department
  KPIs (headcount, turnover, avg salary/tenure), the company-wide attrition
  risk distribution, and a filterable at-risk employee table. Manager sees
  the same risk table scoped to their own direct reports (via the logged-in
  user's `employee_id`, now returned by `GET /auth/me`).
- **`dashboards/dash_app/`** — Executive and Data Scientist. Executive gets
  company-wide KPIs and charts; Data Scientist gets recent drift reports, a
  company-wide risk table, and a button that fires `POST /drift-reports/check`.

A new `executive` role (read-only: `employees:read`, `salaries:read`,
`predictions:read`, `audit:read`) was added in this module's migration —
Module 3's seed never actually created one, despite the product description
always naming it as a dashboard persona.

`dashboards/common/` holds the shared REST client (login, token, `/auth/me`)
and the chart color palette (categorical hues in fixed order; risk level
mapped 1:1 onto a reserved good/warning/serious/critical status palette).

```bash
# backend must be running first (see ML Inference API above)
PYTHONPATH=dashboards poetry run streamlit run dashboards/streamlit_app/app.py
PYTHONPATH=dashboards poetry run python dashboards/dash_app/app.py
```

## Frontend

`frontend/` is the general-purpose HR/employee-portal SPA (React 19 +
TypeScript + Vite + Tailwind CSS v4), the day-to-day CRUD complement to the
analytics-focused dashboards above — same idea, different job: browse and
edit employees/departments, work salary/promotion history, review
per-employee attrition predictions and act on recommendations, read
notifications. Every request goes through the same REST API as everything
else in this repo; nothing here talks to Postgres directly.

- **`src/api/`** — a small typed `fetch` wrapper (`client.ts`) plus
  TanStack Query hooks (`queries.ts`) for every resource the UI touches.
- **`src/auth/`** — `AuthProvider` (JWT in `localStorage`, `/auth/me`
  rehydration on load) and a `permissions.ts` mirror of the seeded
  role/permission table, used to decide what to render — the API remains
  the actual enforcement point regardless of what the UI shows.
- **`src/pages/`** — Employees (search/filter/paginate, create, an
  inline-editable 360 profile with Salary/Promotions/Predictions tabs),
  Departments (CRUD), Notifications.

```bash
cd frontend
cp .env.example .env    # point VITE_API_BASE_URL at the running backend
pnpm install
pnpm dev                # http://localhost:5173
pnpm test                # Vitest + Testing Library
pnpm build               # tsc -b && vite build
```

## Full stack (Docker Compose)

Everything above — Postgres, Redis, an MLflow tracking server, the backend
API, a combined Celery worker+beat, both dashboards, and the frontend — as
one Compose stack, each service built from its own `Dockerfile` (repo
root as build context, since backend/ml/dashboards cross-import each other
or read `db/sql/*.sql`; see each Dockerfile's header comment):

```bash
docker compose -f docker/docker-compose.yml up --build
```

| Service | Port | Notes |
|---|---|---|
| `frontend` | [:8080](http://localhost:8080) | nginx serving the built SPA |
| `backend` | [:8000](http://localhost:8000) | FastAPI; `migrate` runs `alembic upgrade head` first and must exit 0 |
| `streamlit` / `dash` | [:8501](http://localhost:8501) / [:8050](http://localhost:8050) | talk to `backend` over the Docker network, not `localhost` |
| `mlflow` | [:5000](http://localhost:5000) | tracking server + registry; `backend`/`celery` point at it via `MLFLOW_TRACKING_URI` |
| `celery` | — | worker + beat (the nightly drift check from the MLOps section) |
| `postgres` / `redis` | :5432 / :6379 | |

First run only, once `backend` reports healthy — the ETL pipeline and a
training run aren't part of automatic startup (they're one-off maintenance
commands, same as running them locally):

```bash
docker compose -f docker/docker-compose.yml exec backend python -m ml.etl.download_seed_dataset
docker compose -f docker/docker-compose.yml exec backend python -m ml.etl.pipeline --target-rows 5000
docker compose -f docker/docker-compose.yml exec backend python -m ml.training.train --quick
```

CI (`.github/workflows/ci.yml`) builds all four images on every push/PR to
validate the Dockerfiles themselves, and pushes them to GHCR
(`ghcr.io/<owner>/<repo>-{backend,dashboards,mlflow,frontend}`) on pushes to
`main`, using the workflow's own `GITHUB_TOKEN` — no registry secrets to
configure.

## Roadmap

The platform is built and tested module by module (see the project plan for full detail):

- [x] **1. Foundations** — monorepo structure, Poetry, pnpm, pre-commit, Docker Compose skeleton, CI skeleton
- [x] **2. Database schema & Alembic migrations** — 21 normalized tables, constraints/indexes, `db/sql` views/triggers/stored function
- [x] **3. Authentication & RBAC** — Argon2 + JWT access/refresh tokens, permission-based authorization, 5 seeded roles
- [x] **4. Core HR domain API** — departments, employees, salaries, performance reviews, promotions, absences, trainings; Repository + Service Layer, pagination/search, centralized error handling
- [x] **5. Notifications & audit log** — Celery-backed async notification delivery, promotion-triggered notifications, read-only audit log API
- [x] **6. Data engineering — dataset generation & ETL pipeline** — real IBM HR Attrition seed data, Pandera validation, bootstrap+jitter synthetic augmentation, bulk load to Postgres
- [x] **7. ML training, benchmarking & MLflow tracking** — 6 models, Optuna tuning, leakage-safe grouped CV, full metric suite, MLflow tracking + model registry
- [x] **8. Explainability (SHAP/LIME) & recommendation engine** — per-prediction SHAP + LIME attribution, actionable-feature-driven recommendations excluding protected attributes
- [x] **9. ML inference API** — MLflow-backed model loading synced to the model registry table, an offline-feature-store-driven prediction/recommendation REST API
- [x] **10. MLOps — drift detection & automated retraining** — KS-test/PSI drift checks between feature-snapshot periods, threshold-triggered retraining with a beats-production promotion gate, nightly Celery Beat schedule
- [x] **11. Dashboards (Streamlit/Dash)** — HR/Manager (Streamlit) and Executive/Data Scientist (Dash) views, reporting REST endpoints backed by Module 2's SQL views, a new `executive` role
- [x] **12. Frontend (React/TypeScript/Tailwind)** — Employees/Departments/Notifications SPA consuming the REST API, JWT auth, role-gated UI, Vitest + Testing Library, oxlint/Prettier, a frontend CI job
- [x] **13. Full Docker Compose stack & complete CI/CD** — Dockerfiles for backend/celery, dashboards, mlflow and frontend; a `migrate` init service; a GHCR-publishing CI job
- [ ] 14. Final documentation (architecture diagrams, technical & user guides)

## License

MIT
