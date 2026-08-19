"""Runs drift detection (ml.monitoring.drift) between two calendar-day
`employee_feature_snapshots` periods and persists one `DataDriftReport` row
per checked feature. Deliberately raises plain `ValueError` rather than an
`app.core.exceptions` type: this module is also usable standalone (a
Celery task, a CLI script) outside of a request context, so translating to
an HTTP-facing error is the caller's job, not this one's."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ml import DataDriftReport, EmployeeFeatureSnapshot
from ml.inference.features import feature_frame
from ml.monitoring.drift import detect_drift


def snapshot_period_range(session: Session) -> tuple[date, date] | None:
    """The calendar-day span of every `employee_feature_snapshots` row on
    record, or `None` if there aren't any yet (a fresh database before the
    ETL pipeline has ever run)."""
    earliest, latest = session.execute(
        select(
            func.min(EmployeeFeatureSnapshot.computed_at),
            func.max(EmployeeFeatureSnapshot.computed_at),
        )
    ).one()
    if earliest is None:
        return None
    # psycopg hands timestamptz columns back localized to the session's
    # timezone setting, not necessarily UTC -- normalize before taking the
    # calendar date, or a non-UTC session can shift it by a day.
    return earliest.astimezone(UTC).date(), latest.astimezone(UTC).date()


def _day_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    return start_dt, end_dt


def _load_period(session: Session, start: date, end: date) -> pd.DataFrame:
    start_dt, end_dt = _day_bounds(start, end)
    snapshots = session.scalars(
        select(EmployeeFeatureSnapshot).where(
            EmployeeFeatureSnapshot.computed_at >= start_dt,
            EmployeeFeatureSnapshot.computed_at < end_dt,
        )
    ).all()
    return feature_frame([s.features for s in snapshots])


def run_drift_check(
    session: Session,
    *,
    reference_start: date,
    reference_end: date,
    current_start: date,
    current_end: date,
) -> list[DataDriftReport]:
    reference = _load_period(session, reference_start, reference_end)
    current = _load_period(session, current_start, current_end)
    if reference.empty or current.empty:
        raise ValueError(
            "Both the reference and current periods need at least one feature snapshot"
        )

    generated_at = datetime.now(UTC)
    reports = [
        DataDriftReport(
            feature_name=finding.feature_name,
            reference_period_start=reference_start,
            reference_period_end=reference_end,
            current_period_start=current_start,
            current_period_end=current_end,
            drift_score=Decimal(str(round(finding.drift_score, 5))),
            drift_detected=finding.drift_detected,
            method=finding.method,
            generated_at=generated_at,
        )
        for finding in detect_drift(reference, current)
    ]
    session.add_all(reports)
    session.flush()
    return reports
