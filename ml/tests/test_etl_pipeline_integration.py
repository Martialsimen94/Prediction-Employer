"""End-to-end ETL integration test on a small sample, loaded into a real
Postgres inside a transaction that's rolled back on teardown (see
backend/tests/conftest.py — ml/tests reuses it via pytest's rootdir
conftest discovery).

Uses a synthetic sample with randomized department names rather than a
literal slice of the real seed CSV: the real seed's department names
("Sales", "Research & Development", ...) may already exist as *committed*
rows in the dev DB from a manual pipeline run (rollback-on-teardown only
isolates what THIS test writes, not uniqueness checks against data other
processes already committed), which would make this test collide with
whatever the dev DB happens to contain.
"""

import uuid
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ml.etl.pipeline import run
from ml.tests.conftest import _row


@dataclass
class SmallSample:
    path: Path
    department_names: tuple[str, str]


@pytest.fixture
def small_sample(tmp_path: Path) -> SmallSample:
    token = uuid.uuid4().hex[:8]
    dept_a, dept_b = f"Integration Test Dept A {token}", f"Integration Test Dept B {token}"
    # Well above the real seed's EmployeeNumber range (~1-2070) and any
    # plausible synthetic-augmentation range from a prior manual run, so
    # EmployeeNumber-derived employee_number/email never collide with
    # already-committed dev data.
    number_base = 900_000 + (uuid.uuid4().int % 90_000)
    rows = [
        _row(number_base + i, Department=dept_a if i % 2 == 0 else dept_b, JobLevel=(i % 5) + 1)
        for i in range(20)
    ]
    sample_path = tmp_path / "sample.csv"
    pd.DataFrame(rows).to_csv(sample_path, index=False)
    return SmallSample(path=sample_path, department_names=(dept_a, dept_b))


def test_pipeline_dry_run_reports_counts_without_touching_db(small_sample: SmallSample) -> None:
    counts = run(input_path=small_sample.path, target_rows=25, dry_run=True)

    assert counts["employees"] == 25
    assert counts["departments"] >= 1
    assert counts["trainings"] == 10


def test_pipeline_loads_a_small_sample_end_to_end(
    small_sample: SmallSample, db_session: Session
) -> None:
    from app.models.department import Department
    from app.models.employee import Employee
    from app.models.ml import EmployeeFeatureSnapshot
    from app.models.salary import Salary
    from ml.etl.features import FEATURE_COLUMNS

    counts = run(input_path=small_sample.path, target_rows=25, dry_run=False, session=db_session)
    db_session.flush()

    departments = db_session.scalars(
        select(Department).where(Department.name.in_(small_sample.department_names))
    ).all()
    assert len(departments) == 2
    assert any(d.manager_id is not None for d in departments)

    department_ids = {d.id for d in departments}
    employees = db_session.scalars(
        select(Employee).where(Employee.department_id.in_(department_ids))
    ).all()
    assert len(employees) == counts["employees"]

    # every employee got a salary, resolved against a real FK id
    employee_ids = {e.id for e in employees}
    salaries = db_session.scalars(select(Salary).where(Salary.employee_id.in_(employee_ids))).all()
    assert len(salaries) == counts["employees"]

    # the department/employee FKs are real, resolved ids -- not leftover
    # source EmployeeNumbers or unresolved references.
    assert all(e.department_id in department_ids for e in employees)

    snapshots = db_session.scalars(
        select(EmployeeFeatureSnapshot).where(EmployeeFeatureSnapshot.employee_id.in_(employee_ids))
    ).all()
    assert len(snapshots) == counts["employee_feature_snapshots"] == counts["employees"]
    assert set(snapshots[0].features) == set(FEATURE_COLUMNS)
