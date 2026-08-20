# Architecture decisions

The notable engineering decisions made while building this platform, and
why — condensed from the module-by-module reasoning already scattered
through commit messages and code comments. Each entry is Decision / Why /
Trade-off, in the order the modules that made them were built.

## Clean Architecture: Repository + Service Layer

**Decision:** every domain resource gets a `Repository` (SQLAlchemy query
logic only), a `Service` (business rules, cross-entity validation,
transaction shape), and thin FastAPI route handlers that just translate
HTTP ↔ service calls.
**Why:** the service layer is the one place business rules live once,
testable without an HTTP client; the repository layer is the one place
that knows SQLAlchemy exists.
**Trade-off:** more files per resource than a framework that lets routes
touch the ORM directly. Worth it once a resource has more than trivial
CRUD (e.g. `PromotionService` also applying the new title to the employee
record and firing a notification, `PredictionService` orchestrating model
load + explanation + persistence).

## Permission-based, not role-based, authorization

**Decision:** endpoints declare `require_permission("employees:write")`,
never `require_role("hr")`; roles are just named bundles of permissions,
seeded in a migration ([Module 3](../../backend/alembic/versions/4a06f51a9827_seed_default_roles_and_permissions.py)).
**Why:** adding a 6th role (`executive`, Module 11) or moving a permission
between roles is a data change, not a code change — no endpoint had to be
touched to add the Executive dashboard's read access.
**Trade-off:** one more indirection to trace when debugging "why can't this
user do X" (user → roles → permissions, not user → role).

## Bootstrap+jitter synthetic augmentation with lineage tracking

**Decision:** scale the real 1,470-row IBM dataset to an "enterprise" row
count by resampling whole real rows with jitter (not independently
resampling each column), and stamp every synthetic row with a `lineage_id`
back to the real row it came from.
**Why:** independent per-column resampling destroys the correlations the
model needs to learn (e.g. `OverTime` + low `JobSatisfaction` → attrition);
resampling whole rows preserves them. The `lineage_id` then lets
`StratifiedGroupKFold` keep a row and its near-duplicate siblings on the
same side of every train/test split — without it, models scored ~0.99 ROC
AUC by partly recognizing near-duplicates rather than the real pattern
(corrected scores: ~0.78-0.80, in line with published benchmarks for this
dataset).
**Trade-off:** synthetic rows are structurally repetitive at the tails
(same real row jittered many times) in a way a fully independent generator
wouldn't be — acceptable here since the goal is realistic *volume* for
demonstrating an enterprise-scale pipeline, not novel synthetic diversity.

## An offline feature store (`employee_feature_snapshots`)

**Decision:** the ETL pipeline snapshots each employee's raw model-input
feature vector (`JobLevel`, `OverTime`, `EnvironmentSatisfaction`, ...) into
its own table, separate from the normalized operational schema.
**Why:** most of the IBM dataset's columns have no natural home in a
normalized HR schema (salary is its own table with history, absences are
their own table, etc.) — but the model was trained on the *raw* dataset's
columns. Re-deriving them from operational tables at inference time would
risk silently drifting from what the model actually learned as the
operational schema evolves; a snapshot taken once at ETL time can't drift
out from under the model.
**Trade-off:** a second copy of some data that's arguably already present
elsewhere (e.g. tenure is derivable from `hire_date`) — accepted for the
guarantee that inference always sees exactly the columns training saw.

## Promotion requires beating the incumbent, not just finishing

**Decision:** [Module 7](../../ml/training/train.py)'s training script
always registers its best run under MLflow's `staging` alias — that's just
"the most recent thing that finished training." Only
[Module 10](../../ml/monitoring/retrain.py)'s automated retraining can move
the `production` alias, and only when the new run's ROC AUC beats whichever
model — `production` if one's ever been promoted, `staging` otherwise — is
currently ahead. The inference API ([Module 9](../../ml/inference/model_loader.py))
prefers `production`, falling back to `staging`.
**Why:** a scheduled retrain triggered by drift is exactly the moment a
data-quality problem is most likely to also be present — gating promotion
on actually being better stops a bad retrain from silently regressing what
users see.
**Trade-off:** a genuinely improved model sits at `staging` until something
promotes it — acceptable since `train.py` is meant to be run deliberately
(a human decides to retrain from scratch), while Module 10's path is meant
to run unattended.

## Recommendations never cite a protected attribute

**Decision:** [`ml/explainability/recommendations.py`](../../ml/explainability/recommendations.py)'s
feature → retention-lever map deliberately excludes `Gender` and
`MaritalStatus`, even when SHAP finds them predictive.
**Why:** an HR platform must never justify — or appear to justify — an
intervention by a protected/demographic attribute, regardless of whether
the underlying correlation is real. `Age`, `EducationField` and raw tenure
counters are excluded too, for a different reason: they're informative to
the model but not levers HR can actually pull.
**Trade-off:** a real, positive SHAP contribution from an excluded feature
just doesn't produce a recommendation for that risk driver — accepted as
strictly required, not a trade-off to weigh.

## Dashboards and frontend are two different products, one API

**Decision:** [Module 11](../../dashboards/)'s Streamlit/Dash apps
(role-specific analytics: KPIs, risk distributions, drift monitoring) and
[Module 12](../../frontend/)'s React SPA (general CRUD: browse/edit
employees, work salary history, act on recommendations) are separate
clients, both calling the same `/api/v1` REST API — neither ever opens a
database connection.
**Why:** analytics-dashboard users (HR leadership, executives, data
scientists) and CRUD-workflow users (HR ops, managers) have different jobs
to be done; forcing them into one UI usually serves neither well.
Routing both through the same API means RBAC is enforced in exactly one
place regardless of which client is asking.
**Trade-off:** client-side role-gating logic (`dashboards/common/colors.py`'s
role checks, `frontend/src/auth/permissions.ts`) is duplicated across three
places (both dashboard apps' `_VIEWS` maps, the frontend). All three are
UX conveniences only — the API's own `require_permission` is the actual
enforcement point, so drift between them is a UX bug, not a security one.

## Purpose-built Docker images over third-party ones where it matters

**Decision:** [Module 13](../../docker/mlflow/Dockerfile)'s `mlflow`
service is a small custom image (`python:3.12-slim` + `pip install
mlflow==<exact poetry.lock version>`) rather than the third-party
`ghcr.io/mlflow/mlflow` image.
**Why:** pinning the tracking server to the *exact* version the client
library in `poetry.lock` resolves to avoids any server/client API drift,
and building on the same base used everywhere else in this repo means the
tools available in that image (pip, curl) are known, not guessed at.
**Trade-off:** one more Dockerfile to keep in sync with `poetry.lock`
(there's a comment at the `pip install` line as a reminder) instead of
`docker pull`-ing a maintained image.
