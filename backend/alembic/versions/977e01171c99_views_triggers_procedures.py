"""views triggers procedures

Revision ID: 977e01171c99
Revises: 4e71e73fb5ee
Create Date: 2026-08-17 19:30:00.000000
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "977e01171c99"
down_revision: str | None = "4e71e73fb5ee"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# repo_root/backend/alembic/versions/<this file>.py -> repo_root/db/sql
_DB_SQL_DIR = Path(__file__).resolve().parents[3] / "db" / "sql"


def _execute_sql_file(filename: str) -> None:
    sql = (_DB_SQL_DIR / filename).read_text(encoding="utf-8")
    op.execute(sql)


def upgrade() -> None:
    _execute_sql_file("views.sql")
    _execute_sql_file("triggers.sql")
    _execute_sql_file("procedures.sql")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_department_turnover_rate(INTEGER, INTEGER)")

    op.execute("DROP TRIGGER IF EXISTS trg_audit_promotions ON promotions")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_salaries ON salaries")
    op.execute("DROP FUNCTION IF EXISTS audit_trigger_fn()")

    for table in (
        "departments",
        "employees",
        "salaries",
        "performance_reviews",
        "promotions",
        "absences",
        "trainings",
        "employee_trainings",
        "skills",
        "users",
        "roles",
        "permissions",
        "ml_model_registry",
        "attrition_predictions",
        "recommendations",
        "notifications",
        "data_drift_reports",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_set_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.execute("DROP VIEW IF EXISTS v_attrition_risk_summary")
    op.execute("DROP VIEW IF EXISTS v_department_kpis")
    op.execute("DROP VIEW IF EXISTS v_employee_360")
