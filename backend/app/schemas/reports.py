"""Response schemas for the reporting endpoints (Module 11), shaped
directly from the `db/sql` views/function they wrap."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import RiskLevel


class DepartmentKPIRead(BaseModel):
    department_id: int
    department_name: str
    active_headcount: int
    terminations_last_12_months: int
    avg_current_salary: Decimal | None
    avg_tenure_years: Decimal | None
    turnover_rate_12mo: Decimal


class RiskDistributionRead(BaseModel):
    low: int
    medium: int
    high: int
    critical: int


class AttritionRiskSummaryRead(BaseModel):
    employee_id: int
    employee_number: str
    first_name: str
    last_name: str
    department_id: int | None
    department_name: str | None
    risk_score: Decimal
    risk_level: RiskLevel
    predicted_at: datetime
    top_features: dict[str, float]


class Employee360Read(BaseModel):
    employee_id: int
    employee_number: str
    first_name: str
    last_name: str
    email: str
    job_title: str
    employment_status: str
    hire_date: date
    tenure_years: Decimal | None
    department_id: int | None
    department_name: str | None
    manager_id: int | None
    manager_name: str | None
    current_salary: Decimal | None
    current_salary_currency: str | None
    latest_performance_score: Decimal | None
    latest_performance_review_date: date | None
    latest_attrition_risk_level: RiskLevel | None
    latest_attrition_risk_score: Decimal | None
    latest_prediction_at: datetime | None
