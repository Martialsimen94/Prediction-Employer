# API reference

All endpoints are versioned under `/api/v1`. Every response and request
schema is generated from the FastAPI app itself — for exact field types and
live request/response examples, run the API and open **`/docs`** (Swagger
UI) or **`/openapi.json`**; this page is the map of *what exists and who's
allowed to call it*, not a field-by-field schema dump.

Every route except `/health`, `/`, and the three unauthenticated `/auth/*`
routes below requires a bearer JWT (`Authorization: Bearer <token>`, from
`POST /auth/login`) and, for most routes, a specific **permission** — see
[Auth & RBAC](#auth--rbac) for what each of the 6 seeded roles actually
holds. `object` in the permission column below means "any authenticated
user, no specific permission" (e.g. your own notifications).

## Auth (`/auth`)

| Method & path | Auth | Notes |
|---|---|---|
| `POST /auth/register` | none | Creates a user with the `employee` role by default |
| `POST /auth/login` | none | Returns an access + refresh token pair |
| `POST /auth/refresh` | none (valid refresh token) | Issues a new token pair |
| `GET /auth/me` | any user | Current user's id/email/roles/`employee_id` |

## Employees (`/employees`)

| Method & path | Permission |
|---|---|
| `GET /employees` | `employees:read` |
| `POST /employees` | `employees:write` |
| `GET /employees/{id}` | `employees:read` |
| `PATCH /employees/{id}` | `employees:write` |
| `DELETE /employees/{id}` | `employees:write` |

## Departments (`/departments`)

Same five-route CRUD shape as employees, same two permissions
(`employees:read` for the GETs, `employees:write` for POST/PATCH/DELETE).

## Nested under an employee

| Resource | Base path | Read | Write |
|---|---|---|---|
| Salaries | `/employees/{id}/salaries` | `salaries:read` | `salaries:write` |
| Performance reviews | `/employees/{id}/performance-reviews` | `employees:read` | `employees:write` |
| Promotions | `/employees/{id}/promotions` | `employees:read` | `employees:write` |
| Absences | `/employees/{id}/absences` | `employees:read` | `employees:write` |
| Training enrollments | `/employees/{id}/trainings` | `employees:read` | `employees:write` |
| Predictions | `/employees/{id}/predictions` | `predictions:read` | `predictions:write` |

Salaries, promotions and predictions are list+create+get only (no
update/delete — they're an append-only ledger by design: a new salary row
closes the previous one's `end_date` rather than editing it in place, and a
prediction is a point-in-time snapshot). Performance reviews, absences and
training enrollments also support `PATCH`; absences also support `DELETE`.

## Training catalog (`/trainings`)

Full CRUD (`GET`/`POST`/`GET {id}`/`PATCH {id}`/`DELETE {id}`), same
`employees:read` / `employees:write` split as above — this is the shared
course catalog, not a per-employee resource.

## Predictions & recommendations

| Method & path | Permission | Notes |
|---|---|---|
| `POST /employees/{id}/predictions` | `predictions:write` | Scores the employee from their latest feature snapshot; persists the prediction + recommendations (Module 9) |
| `GET /employees/{id}/predictions` | `predictions:read` | Paginated prediction history |
| `GET /predictions/{id}` | `predictions:read` | One prediction with its recommendations |
| `PATCH /recommendations/{id}` | `predictions:write` | Update a recommendation's status |

## Drift & MLOps (`/drift-reports`)

| Method & path | Permission | Notes |
|---|---|---|
| `GET /drift-reports` | `predictions:read` | Filterable by `feature_name` / `drift_detected` |
| `POST /drift-reports/check` | `predictions:write` | Enqueues the async drift-check-and-maybe-retrain Celery task (Module 10) |

## Reporting (`/reports`)

Read-only, backed directly by the `db/sql` views/function from Module 2
(see [`docs/architecture/erd.md`](../architecture/erd.md)) — the data
source Module 11's dashboards and Module 12's frontend both read through.

| Method & path | Permission |
|---|---|
| `GET /reports/department-kpis` | `employees:read` |
| `GET /reports/risk-distribution` | `predictions:read` |
| `GET /reports/attrition-risk-summary` | `predictions:read` |
| `GET /reports/employees/{id}/360` | `employees:read` |

## Notifications (`/notifications`)

Always scoped to the calling user — no permission beyond being logged in,
since there's no meaningful sense in which one user's notifications are
"readable" by role.

| Method & path |
|---|
| `GET /notifications` |
| `GET /notifications/{id}` |
| `PATCH /notifications/{id}/read` |

## Audit log (`/audit-log`)

| Method & path | Permission | Notes |
|---|---|---|
| `GET /audit-log` | `audit:read` | Read-only; rows are written by Postgres triggers ([`db/sql/triggers.sql`](../../db/sql/triggers.sql)), not application code |

## Auth & RBAC

8 permissions, 6 seeded roles ([Module 3](../../backend/alembic/versions/4a06f51a9827_seed_default_roles_and_permissions.py),
[Module 11](../../backend/alembic/versions/d71f9bb415d4_seed_executive_role.py)):

| Role | Permissions |
|---|---|
| `admin` | all 8 |
| `hr` | `employees:read/write`, `salaries:read/write`, `predictions:read`, `audit:read` |
| `manager` | `employees:read`, `predictions:read` |
| `executive` | `employees:read`, `salaries:read`, `predictions:read`, `audit:read` |
| `data_scientist` | `predictions:read/write`, `audit:read` |
| `employee` | none — self-service only (their own notifications, `/auth/me`) |

`users:manage` exists as a permission but nothing in the API currently
requires it — role/permission assignment is a database-seed concern for
now, not yet exposed as an endpoint.
