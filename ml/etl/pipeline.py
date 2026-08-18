"""End-to-end ETL orchestration: extract -> validate -> clean -> augment ->
transform -> load.

Run from the repo root (needs `app.*` importable, hence PYTHONPATH=backend):

    PYTHONPATH=backend poetry run python -m ml.etl.pipeline --target-rows 5000

Use --dry-run to run every stage except the DB load (useful to sanity-check
timings/row counts without touching Postgres).
"""

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pandera as pa

from ml.etl import clean as clean_stage
from ml.etl import load as load_stage
from ml.etl import synthetic as synthetic_stage
from ml.etl import transform as transform_stage
from ml.etl.extract import extract
from ml.etl.schema import RawAttritionSchema

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

DEFAULT_SEED_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "raw" / ("WA_Fn-UseC_-HR-Employee-Attrition.csv")
)
DEFAULT_TARGET_ROWS = 5000
RANDOM_STATE = 42


def run(
    *,
    input_path: Path = DEFAULT_SEED_PATH,
    target_rows: int = DEFAULT_TARGET_ROWS,
    dry_run: bool = False,
    session: "Session | None" = None,
) -> dict[str, int]:
    """If `session` is given, records are loaded into it but NOT committed —
    the caller owns the transaction (tests pass in a rolled-back-on-teardown
    session; the CLI leaves `session` unset and commits its own)."""
    raw_df = extract(input_path)
    validated_df = RawAttritionSchema.validate(raw_df, lazy=True)

    cleaned_df = clean_stage.clean(validated_df)
    augmented_df = synthetic_stage.augment(
        cleaned_df, target_rows=target_rows, random_state=RANDOM_STATE
    )
    augmented_df = augmented_df.drop(columns=["is_outlier"], errors="ignore")

    departments_df = transform_stage.build_departments(augmented_df)
    with_managers_df = transform_stage.assign_managers(augmented_df)
    department_manager_numbers = transform_stage.department_managers(with_managers_df)

    employee_records = transform_stage.to_employee_records(
        with_managers_df, random_state=RANDOM_STATE
    )
    salary_records = transform_stage.to_salary_records(employee_records)
    review_records = transform_stage.to_performance_review_records(
        employee_records, random_state=RANDOM_STATE
    )
    absence_records = transform_stage.to_absence_records(
        employee_records, random_state=RANDOM_STATE
    )
    enrollment_records = transform_stage.to_employee_training_records(
        employee_records, random_state=RANDOM_STATE
    )

    counts = {
        "departments": len(departments_df),
        "employees": len(employee_records),
        "salaries": len(salary_records),
        "performance_reviews": len(review_records),
        "absences": len(absence_records),
        "trainings": len(transform_stage.TRAINING_CATALOG),
        "employee_trainings": len(enrollment_records),
    }

    if dry_run:
        return counts

    def _load(target_session: "Session") -> None:
        department_ids = load_stage.load_departments(target_session, departments_df)
        employee_number_to_id = load_stage.load_employees(
            target_session, employee_records, department_ids
        )
        load_stage.set_department_managers(
            target_session, department_ids, department_manager_numbers, employee_number_to_id
        )
        load_stage.load_salaries(target_session, salary_records, employee_number_to_id)
        load_stage.load_performance_reviews(target_session, review_records, employee_number_to_id)
        load_stage.load_absences(target_session, absence_records, employee_number_to_id)
        training_ids = load_stage.load_training_catalog(target_session)
        load_stage.load_employee_trainings(
            target_session, enrollment_records, employee_number_to_id, training_ids
        )

    if session is not None:
        _load(session)
        return counts

    from app.core.db import SessionLocal

    with SessionLocal() as owned_session:
        _load(owned_session)
        owned_session.commit()

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_SEED_PATH)
    parser.add_argument("--target-rows", type=int, default=DEFAULT_TARGET_ROWS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        counts = run(input_path=args.input, target_rows=args.target_rows, dry_run=args.dry_run)
    except pa.errors.SchemaErrors as exc:
        print("Schema validation failed:", file=sys.stderr)  # noqa: T201
        print(exc.failure_cases, file=sys.stderr)  # noqa: T201
        return 1

    for table, count in counts.items():
        print(f"{table}: {count}")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
