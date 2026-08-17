"""Salary request/response schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SalaryChangeReason


class SalaryCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    effective_date: date
    reason: SalaryChangeReason


class SalaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    amount: Decimal
    currency: str
    effective_date: date
    end_date: date | None
    reason: SalaryChangeReason
