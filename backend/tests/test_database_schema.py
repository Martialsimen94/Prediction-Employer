"""Integration tests against a real PostgreSQL database: schema, constraints,
triggers, views and the turnover-rate stored function.

Requires a reachable database (see .env / POSTGRES_DSN); skipped otherwise.
Every test runs inside a transaction that is rolled back on teardown, so no
state leaks between tests or into the shared dev database.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import EmploymentStatus, SalaryChangeReason
from app.models.salary import Salary

CORE_TABLES = {
    "employees",
    "departments",
    "salaries",
    "performance_reviews",
    "promotions",
    "absences",
    "trainings",
    "employee_trainings",
    "skills",
    "employee_skills",
    "users",
    "roles",
    "permissions",
    "attrition_predictions",
    "recommendations",
    "notifications",
    "audit_log",
    "ml_model_registry",
    "data_drift_reports",
}


def _make_department(session: Session, name: str) -> Department:
    department = Department(name=name)
    session.add(department)
    session.flush()
    return department


def _make_employee(
    session: Session, department: Department, *, email: str, employee_number: str
) -> Employee:
    employee = Employee(
        employee_number=employee_number,
        first_name="Ada",
        last_name="Lovelace",
        email=email,
        hire_date=date(2020, 1, 15),
        department_id=department.id,
        job_title="Staff Engineer",
        employment_status=EmploymentStatus.ACTIVE,
    )
    session.add(employee)
    session.flush()
    return employee


def test_core_tables_exist(db_connection: Connection) -> None:
    rows = db_connection.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    )
    existing = {row[0] for row in rows}
    assert existing >= CORE_TABLES


def test_salary_amount_must_be_positive(db_session: Session) -> None:
    department = _make_department(db_session, "Engineering")
    employee = _make_employee(
        db_session, department, email="neg-salary@example.com", employee_number="E-NEG"
    )

    db_session.add(
        Salary(
            employee_id=employee.id,
            amount=Decimal("-100.00"),
            effective_date=date(2020, 1, 15),
            reason=SalaryChangeReason.INITIAL,
        )
    )
    with pytest.raises(IntegrityError, match="ck_salaries_amount_positive"):
        db_session.flush()


def test_employee_email_must_be_unique(db_session: Session) -> None:
    department = _make_department(db_session, "Engineering")
    _make_employee(db_session, department, email="dup@example.com", employee_number="E-1")

    db_session.add(
        Employee(
            employee_number="E-2",
            first_name="Grace",
            last_name="Hopper",
            email="dup@example.com",
            hire_date=date(2021, 1, 1),
            department_id=department.id,
            job_title="Principal Engineer",
            employment_status=EmploymentStatus.ACTIVE,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_department_can_reference_employee_as_manager(db_session: Session) -> None:
    department = _make_department(db_session, "Engineering")
    manager = _make_employee(
        db_session, department, email="manager@example.com", employee_number="E-MGR"
    )

    department.manager_id = manager.id
    db_session.flush()

    refreshed = db_session.get(Department, department.id)
    assert refreshed is not None
    assert refreshed.manager_id == manager.id


def test_salary_changes_are_audited(db_session: Session) -> None:
    department = _make_department(db_session, "Engineering")
    employee = _make_employee(
        db_session, department, email="audited@example.com", employee_number="E-AUDIT"
    )
    salary = Salary(
        employee_id=employee.id,
        amount=Decimal("95000.00"),
        effective_date=date(2020, 1, 15),
        reason=SalaryChangeReason.INITIAL,
    )
    db_session.add(salary)
    db_session.flush()

    salary.amount = Decimal("97000.00")
    db_session.flush()

    rows = db_session.execute(
        text(
            "SELECT action, old_data->>'amount' AS old_amount, new_data->>'amount' AS new_amount "
            "FROM audit_log WHERE table_name = 'salaries' AND record_id = :id ORDER BY id"
        ),
        {"id": salary.id},
    ).all()

    assert [r.action for r in rows] == ["INSERT", "UPDATE"]
    assert rows[1].old_amount == "95000.00"
    assert rows[1].new_amount == "97000.00"


def test_department_turnover_rate_function(db_session: Session) -> None:
    department = _make_department(db_session, "Sales")
    employee = _make_employee(
        db_session, department, email="turnover@example.com", employee_number="E-TURN"
    )
    db_session.flush()

    before = db_session.execute(
        text("SELECT fn_department_turnover_rate(:dept_id, 12)"), {"dept_id": department.id}
    ).scalar_one()
    assert before == Decimal("0.00")

    employee.employment_status = EmploymentStatus.TERMINATED
    employee.termination_date = date.today() - timedelta(days=1)
    db_session.flush()

    after = db_session.execute(
        text("SELECT fn_department_turnover_rate(:dept_id, 12)"), {"dept_id": department.id}
    ).scalar_one()
    assert after == Decimal("100.00")


def test_v_employee_360_view(db_session: Session) -> None:
    department = _make_department(db_session, "Engineering")
    employee = _make_employee(
        db_session, department, email="view360@example.com", employee_number="E-VIEW"
    )
    db_session.add(
        Salary(
            employee_id=employee.id,
            amount=Decimal("120000.00"),
            effective_date=date(2020, 1, 15),
            reason=SalaryChangeReason.INITIAL,
        )
    )
    db_session.flush()

    row = db_session.execute(
        text("SELECT department_name, current_salary FROM v_employee_360 WHERE employee_id = :id"),
        {"id": employee.id},
    ).one()

    assert row.department_name == "Engineering"
    assert row.current_salary == Decimal("120000.00")
