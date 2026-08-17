"""Employee request/response schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import EmploymentStatus


class EmployeeCreate(BaseModel):
    employee_number: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    hire_date: date
    birth_date: date | None = None
    department_id: int | None = None
    manager_id: int | None = None
    job_title: str = Field(min_length=1, max_length=150)
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    gender: str | None = Field(default=None, max_length=30)
    marital_status: str | None = Field(default=None, max_length=30)
    education_level: str | None = Field(default=None, max_length=50)
    distance_from_home_km: Decimal | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    department_id: int | None = None
    manager_id: int | None = None
    job_title: str | None = Field(default=None, min_length=1, max_length=150)
    employment_status: EmploymentStatus | None = None
    termination_date: date | None = None
    gender: str | None = Field(default=None, max_length=30)
    marital_status: str | None = Field(default=None, max_length=30)
    education_level: str | None = Field(default=None, max_length=50)
    distance_from_home_km: Decimal | None = None


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_number: str
    first_name: str
    last_name: str
    email: str
    hire_date: date
    birth_date: date | None
    department_id: int | None
    manager_id: int | None
    job_title: str
    employment_status: EmploymentStatus
    termination_date: date | None
    gender: str | None
    marital_status: str | None
    education_level: str | None
    distance_from_home_km: Decimal | None
