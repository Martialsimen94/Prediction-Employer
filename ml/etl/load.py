"""Load: bulk-insert transformed records into Postgres via SQLAlchemy Core
(not the ORM Session.add() pattern used by the API — at ETL scale, batched
INSERT...RETURNING is far faster than one flush per row).

EmployeeNumber-based references from transform.py are resolved into real
database ids here, in dependency order: departments -> employees -> (their
manager_id, and their department's manager_id) -> salaries / performance
reviews / absences -> the training catalog -> employee training enrollments.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Table, bindparam, insert, select
from sqlalchemy.orm import Session, decl_api

from app.models.absence import Absence
from app.models.department import Department
from app.models.employee import Employee
from app.models.ml import EmployeeFeatureSnapshot
from app.models.performance_review import PerformanceReview
from app.models.salary import Salary
from app.models.training import EmployeeTraining, Training
from ml.etl.features import FEATURE_COLUMNS
from ml.etl.transform import TRAINING_CATALOG


def _table(model: type[decl_api.DeclarativeBase]) -> Table:
    """`Model.__table__` is typed as the broader FromClause by SQLAlchemy's
    declarative stubs; it's always a concrete Table at runtime for our
    single-table models."""
    return cast(Table, model.__table__)


def _bulk_insert_returning_ids(
    session: Session, table: Table, rows: Sequence[dict[str, Any]]
) -> list[int]:
    if not rows:
        return []
    stmt = insert(table).returning(table.c.id, sort_by_parameter_order=True)
    result = session.execute(stmt, list(rows))
    return [row[0] for row in result.fetchall()]


def load_departments(session: Session, departments_df: pd.DataFrame) -> dict[str, int]:
    ids = _bulk_insert_returning_ids(session, _table(Department), departments_df.to_dict("records"))
    return dict(zip(departments_df["name"], ids, strict=True))


def load_employees(
    session: Session, employee_records: pd.DataFrame, department_ids: dict[str, int]
) -> dict[int, int]:
    """Returns {source EmployeeNumber: real DB id}. manager_id is set in a
    second pass (bulk UPDATE) since it isn't known until ids are assigned."""
    rows = [
        {
            "employee_number": r.employee_number,
            "first_name": r.first_name,
            "last_name": r.last_name,
            "email": r.email,
            "hire_date": r.hire_date,
            "birth_date": r.birth_date,
            "department_id": department_ids[r.department_name],
            "job_title": r.job_title,
            "employment_status": r.employment_status,
            "termination_date": r.termination_date,
            "gender": r.gender,
            "marital_status": r.marital_status,
            "education_level": r.education_level,
            "distance_from_home_km": r.distance_from_home_km,
        }
        for r in employee_records.itertuples(index=False)
    ]
    ids = _bulk_insert_returning_ids(session, _table(Employee), rows)
    employee_number_to_id = dict(zip(employee_records["source_employee_number"], ids, strict=True))

    manager_updates = [
        {
            "_id": employee_number_to_id[int(source_num)],
            "manager_id": employee_number_to_id[int(manager_num)],
        }
        for source_num, manager_num in zip(
            employee_records["source_employee_number"],
            employee_records["manager_employee_number"],
            strict=True,
        )
        if pd.notna(manager_num)
    ]
    if manager_updates:
        session.execute(
            _table(Employee).update().where(_table(Employee).c.id == bindparam("_id")),
            manager_updates,
        )

    return employee_number_to_id


def set_department_managers(
    session: Session,
    department_ids: dict[str, int],
    department_manager_employee_numbers: dict[str, int],
    employee_number_to_id: dict[int, int],
) -> None:
    updates = [
        {
            "_id": department_ids[department_name],
            "manager_id": employee_number_to_id[manager_employee_number],
        }
        for department_name, manager_employee_number in department_manager_employee_numbers.items()
    ]
    if updates:
        session.execute(
            _table(Department).update().where(_table(Department).c.id == bindparam("_id")),
            updates,
        )


def load_salaries(
    session: Session, salary_records: pd.DataFrame, employee_number_to_id: dict[int, int]
) -> None:
    rows = [
        {
            "employee_id": employee_number_to_id[int(r.source_employee_number)],
            "amount": r.amount,
            "currency": r.currency,
            "effective_date": r.effective_date,
            "reason": r.reason,
        }
        for r in salary_records.itertuples(index=False)
    ]
    session.execute(insert(_table(Salary)), rows)


def load_performance_reviews(
    session: Session, review_records: pd.DataFrame, employee_number_to_id: dict[int, int]
) -> None:
    rows = [
        {
            "employee_id": employee_number_to_id[int(r.source_employee_number)],
            "review_date": r.review_date,
            "review_period": r.review_period,
            "score": r.score,
        }
        for r in review_records.itertuples(index=False)
    ]
    session.execute(insert(_table(PerformanceReview)), rows)


def load_absences(
    session: Session, absence_records: pd.DataFrame, employee_number_to_id: dict[int, int]
) -> None:
    if absence_records.empty:
        return
    rows = [
        {
            "employee_id": employee_number_to_id[int(r.source_employee_number)],
            "absence_type": r.absence_type,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "approved": r.approved,
        }
        for r in absence_records.itertuples(index=False)
    ]
    session.execute(insert(_table(Absence)), rows)


def load_employee_feature_snapshots(
    session: Session,
    feature_records: pd.DataFrame,
    employee_number_to_id: dict[int, int],
    *,
    computed_at: datetime,
) -> None:
    """One row per employee, populating the offline feature store Module 9's
    inference API reads back to reconstruct exactly what the model was
    trained on (see `ml.etl.transform.to_employee_feature_records`)."""
    feature_dicts = feature_records[FEATURE_COLUMNS].to_dict("records")
    rows = [
        {
            "employee_id": employee_number_to_id[int(source_number)],
            "features": features,
            "computed_at": computed_at,
        }
        for source_number, features in zip(
            feature_records["source_employee_number"], feature_dicts, strict=True
        )
    ]
    session.execute(insert(_table(EmployeeFeatureSnapshot)), rows)


def load_training_catalog(session: Session) -> list[int]:
    """Idempotent: inserts only the catalog entries that don't already
    exist (by name), and returns ids for the *whole* catalog, in
    TRAINING_CATALOG order — running the pipeline again must not fail on
    trainings.name's unique constraint, nor create duplicate courses."""
    catalog_names = [name for name, *_ in TRAINING_CATALOG]
    existing = session.execute(
        select(_table(Training).c.name, _table(Training).c.id).where(
            _table(Training).c.name.in_(catalog_names)
        )
    ).all()
    existing_ids: dict[str, int] = {name: id_ for name, id_ in existing}

    missing_rows = [
        {"name": name, "provider": provider, "category": category, "duration_hours": hours}
        for name, provider, category, hours in TRAINING_CATALOG
        if name not in existing_ids
    ]
    new_ids = _bulk_insert_returning_ids(session, _table(Training), missing_rows)
    missing_names = [str(row["name"]) for row in missing_rows]
    existing_ids.update(zip(missing_names, new_ids, strict=True))

    return [existing_ids[name] for name in catalog_names]


def load_employee_trainings(
    session: Session,
    enrollment_records: pd.DataFrame,
    employee_number_to_id: dict[int, int],
    training_ids: list[int],
) -> None:
    if enrollment_records.empty:
        return
    rows = [
        {
            "employee_id": employee_number_to_id[int(r.source_employee_number)],
            "training_id": training_ids[int(r.training_index)],
            "start_date": r.start_date,
            "completion_date": r.completion_date,
            "status": r.status,
            "score": r.score,
        }
        for r in enrollment_records.itertuples(index=False)
    ]
    session.execute(insert(_table(EmployeeTraining)), rows)
