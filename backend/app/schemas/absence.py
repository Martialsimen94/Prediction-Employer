"""Absence request/response schemas."""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import AbsenceType


class AbsenceCreate(BaseModel):
    absence_type: AbsenceType
    start_date: date
    end_date: date
    approved: bool = False

    @model_validator(mode="after")
    def check_date_order(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class AbsenceUpdate(BaseModel):
    approved: bool | None = None


class AbsenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    absence_type: AbsenceType
    start_date: date
    end_date: date
    approved: bool
