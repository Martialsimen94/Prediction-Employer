"""Reporting endpoints (Module 11): department KPIs, attrition risk
distribution/summary and a consolidated per-employee view, all backed by
the `db/sql` views/function (Module 2) — the data source the dashboards
were always meant to read through this API rather than querying directly."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.models.enums import RiskLevel
from app.schemas.common import Page
from app.schemas.reports import (
    AttritionRiskSummaryRead,
    DepartmentKPIRead,
    Employee360Read,
    RiskDistributionRead,
)
from app.services.reports_service import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/department-kpis", response_model=list[DepartmentKPIRead])
def department_kpis(
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> list[DepartmentKPIRead]:
    return [DepartmentKPIRead.model_validate(row) for row in ReportsService(db).department_kpis()]


@router.get("/risk-distribution", response_model=RiskDistributionRead)
def risk_distribution(
    department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("predictions:read")),
) -> RiskDistributionRead:
    counts = ReportsService(db).risk_distribution(department_id=department_id)
    return RiskDistributionRead.model_validate(counts)


@router.get("/attrition-risk-summary", response_model=Page[AttritionRiskSummaryRead])
def attrition_risk_summary(
    department_id: int | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    manager_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("predictions:read")),
) -> Page[AttritionRiskSummaryRead]:
    items, total = ReportsService(db).attrition_risk_summary(
        department_id=department_id,
        risk_level=risk_level,
        manager_id=manager_id,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[AttritionRiskSummaryRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/employees/{employee_id}/360", response_model=Employee360Read)
def employee_360(
    employee_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> Employee360Read:
    return Employee360Read.model_validate(ReportsService(db).employee_360(employee_id))
