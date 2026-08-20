# User guide

This platform has two places you might sign in, with the same email and
password either way — which one you want depends on what you're doing:

- **The app** (`http://localhost:8080` once the [full stack](../../README.md#full-stack-docker-compose)
  is running) — day-to-day work: look up an employee, record a salary
  change or promotion, check your notifications.
- **The dashboards** (`http://localhost:8501` for HR/Manager,
  `http://localhost:8050` for Executive/Data Scientist) — read-heavy
  analytics: KPIs, attrition risk across the company or your team, drift
  monitoring.

What you see in either place depends on your role. If something described
below isn't showing up for you, you likely don't have that role — ask an
admin.

## Everyone

Whatever your role, **Notifications** (in the app's top nav) is yours —
it's always scoped to you, with no permission required. You'll get one
automatically when you're promoted, for example.

## Employee

No dashboards, no employee-management screens — self-service only. Sign
into the app, check your notifications. If you also happen to be a
manager, HR, etc., you'll have that role's access too (roles stack; they
aren't mutually exclusive).

## Manager

- **App:** browse employees, open anyone's profile to see their
  compensation history, promotions, and (read-only) attrition predictions.
- **Streamlit dashboard → Manager tab:** your own team only, scoped
  automatically from your account — a roster of your direct reports and
  their attrition risk, sorted highest-risk first. No setup needed; it
  looks up who reports to you from your linked employee record.

## HR

- **App:** full employee and department management — create/edit
  employees, record salary changes and promotions, manage the training
  catalog. You can see attrition predictions and recommendations but can't
  trigger a new prediction or change a recommendation's status — that's
  the Data Scientist's / an admin's call.
- **Streamlit dashboard → HR tab:** department KPIs (headcount, turnover,
  average salary and tenure), the company-wide attrition risk breakdown,
  and a filterable "employees at risk" table.

## Executive

Read-only, company-wide — no employee-editing screens, this role is about
visibility, not operations.

- **Dash dashboard → Executive tab:** headcount by department, company-wide
  turnover, and the attrition risk distribution, all in one view.
- **App:** can browse employee records and salary history (read-only) if
  you need to look something up directly.

## Data Scientist

The MLOps operator role — triggers the things that cost compute, sees the
model-health signals that justify doing so.

- **App:** on any employee's profile, the **Predictions** tab has a "Run
  new prediction" button (scores them from their latest ETL feature
  snapshot) and lets you update a recommendation's status
  (pending → in progress → completed/dismissed) as retention actions get
  worked.
- **Dash dashboard → Data Scientist tab:** recent drift reports, the
  company-wide risk table, and a "Run drift check now" button that queues
  the same drift-check-and-maybe-retrain job the nightly schedule runs
  (Module 10) — useful right after loading fresh data instead of waiting
  for the schedule.

Note: this role doesn't include general employee browsing (`employees:read`)
by design — its job is scoring and monitoring, not HR record-keeping — so
you won't see an "Employees" link in the app's nav. Predictions and
recommendations are reached through the dashboards' aggregate views
instead of browsing to an individual employee.

## Admin

Everything above, all at once — every permission, every dashboard tab,
full CRUD everywhere. Use it for account setup and troubleshooting, not as
a default role: day-to-day work is easier from a role scoped to the actual
job.

## Typical workflow: acting on a prediction

1. **Data Scientist** runs (or waits for the nightly scheduled) drift
   check; if enough features have drifted, retraining kicks off
   automatically and — only if the result is actually better — gets
   promoted to production.
2. **Data Scientist** (or the nightly job, once predictions are wired to
   run automatically in a future module) scores at-risk employees from an
   employee's Predictions tab.
3. **HR** or the employee's **Manager** sees the resulting risk level and
   recommendations — in the app on that employee's profile, or in the
   dashboards' at-risk tables.
4. **Data Scientist** (today) or **HR** (once write access extends to
   recommendations) marks a recommendation `in_progress` once someone
   starts acting on it, `completed` once it's done.
