"""Data access for the offline feature store (Module 6's ETL output)."""

from collections.abc import Sequence

from sqlalchemy import func, select

from app.models.ml import EmployeeFeatureSnapshot
from app.repositories.base import BaseRepository


class FeatureSnapshotRepository(BaseRepository[EmployeeFeatureSnapshot]):
    model = EmployeeFeatureSnapshot

    def get_by_employee_id(self, employee_id: int) -> EmployeeFeatureSnapshot | None:
        return self._session.scalar(
            select(EmployeeFeatureSnapshot).where(
                EmployeeFeatureSnapshot.employee_id == employee_id
            )
        )

    def sample(self, *, limit: int = 200) -> Sequence[EmployeeFeatureSnapshot]:
        """A random sample used as the SHAP/LIME background distribution
        (see ml/explainability/explain.py) — not an exhaustive scan, since
        the dataset can run into the thousands of employees."""
        stmt = select(EmployeeFeatureSnapshot).order_by(func.random()).limit(limit)
        return self._session.scalars(stmt).all()
