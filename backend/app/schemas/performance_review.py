"""Performance review request/response schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PerformanceReviewCreate(BaseModel):
    reviewer_id: int | None = None
    review_date: date
    review_period: str = Field(min_length=1, max_length=20)
    score: Decimal = Field(ge=0, le=5)
    comments: str | None = None


class PerformanceReviewUpdate(BaseModel):
    score: Decimal | None = Field(default=None, ge=0, le=5)
    comments: str | None = None


class PerformanceReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    reviewer_id: int | None
    review_date: date
    review_period: str
    score: Decimal
    comments: str | None
