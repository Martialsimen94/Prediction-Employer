"""Promotion request/response schemas."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PromotionCreate(BaseModel):
    previous_job_title: str = Field(min_length=1, max_length=150)
    new_job_title: str = Field(min_length=1, max_length=150)
    previous_department_id: int | None = None
    new_department_id: int | None = None
    promotion_date: date
    approved_by: int | None = None


class PromotionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    previous_job_title: str
    new_job_title: str
    previous_department_id: int | None
    new_department_id: int | None
    promotion_date: date
    approved_by: int | None
