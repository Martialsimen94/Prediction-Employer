"""Training catalog and per-employee enrollment schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TrainingStatus


class TrainingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider: str | None = Field(default=None, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    duration_hours: int = Field(gt=0, le=32767)


class TrainingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    provider: str | None = None
    category: str | None = None
    duration_hours: int | None = Field(default=None, gt=0, le=32767)


class TrainingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider: str | None
    category: str | None
    duration_hours: int


class EmployeeTrainingCreate(BaseModel):
    training_id: int
    start_date: date
    status: TrainingStatus = TrainingStatus.ENROLLED


class EmployeeTrainingUpdate(BaseModel):
    completion_date: date | None = None
    status: TrainingStatus | None = None
    score: Decimal | None = Field(default=None, ge=0, le=100)


class EmployeeTrainingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    training_id: int
    start_date: date
    completion_date: date | None
    status: TrainingStatus
    score: Decimal | None
