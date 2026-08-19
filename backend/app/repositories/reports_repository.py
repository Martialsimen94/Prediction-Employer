"""Read-only access to the reporting views and turnover stored function
(`db/sql/`, Module 2) that back the dashboards (Module 11). Plain SQL
rather than the ORM: these are reporting views, not domain tables owned by
a model, and the point of `db/sql` was always to let this kind of query
live in the database rather than be reimplemented in Python."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class ReportsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def department_kpis(self) -> Sequence[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT
                    k.department_id,
                    k.department_name,
                    k.active_headcount,
                    k.terminations_last_12_months,
                    k.avg_current_salary,
                    k.avg_tenure_years,
                    fn_department_turnover_rate(k.department_id, 12) AS turnover_rate_12mo
                FROM v_department_kpis k
                ORDER BY k.department_name
                """
            )
        )
        return [dict(row) for row in rows.mappings().all()]

    def risk_distribution(self, *, department_id: int | None) -> dict[str, int]:
        # Explicit casts throughout: Postgres can't infer a bare bind
        # parameter's type from an `IS NULL` check alone (it's polymorphic),
        # and psycopg's extended query protocol needs every parameter typed
        # up front -- without the cast this raises "could not determine
        # data type of parameter $1".
        rows = self._session.execute(
            text(
                """
                SELECT risk_level, COUNT(*) AS employee_count
                FROM v_attrition_risk_summary
                WHERE CAST(:department_id AS INTEGER) IS NULL
                   OR department_id = CAST(:department_id AS INTEGER)
                GROUP BY risk_level
                """
            ),
            {"department_id": department_id},
        )
        return {risk_level: count for risk_level, count in rows.all()}

    def attrition_risk_summary(
        self,
        *,
        department_id: int | None,
        risk_level: str | None,
        manager_id: int | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[dict[str, Any]], int]:
        where_sql = """
            (CAST(:department_id AS INTEGER) IS NULL
                OR v.department_id = CAST(:department_id AS INTEGER))
            AND (CAST(:risk_level AS risk_level) IS NULL
                OR v.risk_level = CAST(:risk_level AS risk_level))
            AND (CAST(:manager_id AS INTEGER) IS NULL
                OR e.manager_id = CAST(:manager_id AS INTEGER))
        """
        params = {
            "department_id": department_id,
            "risk_level": risk_level,
            "manager_id": manager_id,
        }

        total = self._session.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM v_attrition_risk_summary v
                JOIN employees e ON e.id = v.employee_id
                WHERE {where_sql}
                """
            ),
            params,
        ).scalar_one()

        rows = self._session.execute(
            text(
                f"""
                SELECT v.*
                FROM v_attrition_risk_summary v
                JOIN employees e ON e.id = v.employee_id
                WHERE {where_sql}
                ORDER BY v.risk_score DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {**params, "limit": limit, "offset": offset},
        )
        return [dict(row) for row in rows.mappings().all()], total

    def employee_360(self, employee_id: int) -> dict[str, Any] | None:
        row = (
            self._session.execute(
                text("SELECT * FROM v_employee_360 WHERE employee_id = :employee_id"),
                {"employee_id": employee_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None
