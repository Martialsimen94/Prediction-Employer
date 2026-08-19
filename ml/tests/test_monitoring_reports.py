"""Integration tests for running + persisting a drift check between two
`employee_feature_snapshots` periods, against a real Postgres (rolled back
on teardown -- see backend/tests/conftest.py)."""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.ml import DataDriftReport, EmployeeFeatureSnapshot
from ml.etl.features import FEATURE_COLUMNS
from ml.monitoring.reports import run_drift_check, snapshot_period_range
from ml.tests.conftest import _row


def _feature_dict(**overrides: Any) -> dict[str, float | str]:
    row = _row(1, **overrides)
    return {column: row[column] for column in FEATURE_COLUMNS}


def _add_employee_snapshot(
    db_session: Session, *, number: str, computed_at: datetime, **feature_overrides: Any
) -> None:
    employee = Employee(
        employee_number=number,
        first_name="Drift",
        last_name=number,
        email=f"{number.lower()}@example.com",
        hire_date=date(2019, 1, 1),
        job_title="Engineer",
    )
    db_session.add(employee)
    db_session.flush()
    db_session.add(
        EmployeeFeatureSnapshot(
            employee_id=employee.id,
            features=_feature_dict(**feature_overrides),
            computed_at=computed_at,
        )
    )
    db_session.flush()


def test_snapshot_period_range_is_none_without_any_snapshots(db_session: Session) -> None:
    assert snapshot_period_range(db_session) is None


def test_snapshot_period_range_spans_earliest_to_latest_batch(db_session: Session) -> None:
    _add_employee_snapshot(
        db_session, number="E-DRIFT-1", computed_at=datetime(2024, 1, 1, tzinfo=UTC)
    )
    _add_employee_snapshot(
        db_session, number="E-DRIFT-2", computed_at=datetime(2024, 3, 15, tzinfo=UTC)
    )

    assert snapshot_period_range(db_session) == (date(2024, 1, 1), date(2024, 3, 15))


def test_run_drift_check_persists_one_report_per_feature_column(db_session: Session) -> None:
    reference_day = datetime(2024, 1, 1, tzinfo=UTC)
    current_day = datetime(2024, 3, 15, tzinfo=UTC)
    for i in range(10):
        _add_employee_snapshot(
            db_session,
            number=f"E-REF-{i}",
            computed_at=reference_day,
            OverTime="Yes" if i % 2 == 0 else "No",
        )
    for i in range(10):
        # A near-total shift to OverTime="Yes" (categorical drift) and a
        # shifted MonthlyIncome (numeric drift).
        _add_employee_snapshot(
            db_session,
            number=f"E-CUR-{i}",
            computed_at=current_day,
            OverTime="Yes",
            MonthlyIncome=50000,
        )

    reports = run_drift_check(
        db_session,
        reference_start=reference_day.date(),
        reference_end=reference_day.date(),
        current_start=current_day.date(),
        current_end=current_day.date(),
    )

    assert {r.feature_name for r in reports} == set(FEATURE_COLUMNS)
    persisted = db_session.scalars(select(DataDriftReport)).all()
    assert len(persisted) == len(FEATURE_COLUMNS)

    overtime_report = next(r for r in reports if r.feature_name == "OverTime")
    assert overtime_report.method == "psi"
    assert overtime_report.drift_detected

    income_report = next(r for r in reports if r.feature_name == "MonthlyIncome")
    assert income_report.method == "ks_test"
    assert income_report.drift_detected


def test_run_drift_check_requires_snapshots_in_both_periods(db_session: Session) -> None:
    _add_employee_snapshot(
        db_session, number="E-ONLY", computed_at=datetime(2024, 1, 1, tzinfo=UTC)
    )

    with pytest.raises(ValueError, match="at least one feature snapshot"):
        run_drift_check(
            db_session,
            reference_start=date(2024, 1, 1),
            reference_end=date(2024, 1, 1),
            current_start=date(2024, 3, 15),
            current_end=date(2024, 3, 15),
        )
