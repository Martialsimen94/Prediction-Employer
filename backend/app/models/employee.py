"""Employee entity — the central record the whole platform revolves around."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import EmploymentStatus

if TYPE_CHECKING:
    from app.models.department import Department


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "termination_date IS NULL OR termination_date >= hire_date",
            name="ck_employees_termination_after_hire",
        ),
        CheckConstraint(
            "manager_id IS NULL OR manager_id <> id", name="ck_employees_not_own_manager"
        ),
        Index("ix_employees_department_id", "department_id"),
        Index("ix_employees_manager_id", "manager_id"),
        Index("ix_employees_employment_status", "employment_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        pg_enum(EmploymentStatus, "employment_status"),
        default=EmploymentStatus.ACTIVE,
        nullable=False,
    )
    termination_date: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(30))
    marital_status: Mapped[str | None] = mapped_column(String(30))
    education_level: Mapped[str | None] = mapped_column(String(50))
    distance_from_home_km: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    department: Mapped["Department | None"] = relationship(  # noqa: F821
        "Department",
        foreign_keys=[department_id],
        back_populates="employees",
    )
    manager: Mapped["Employee | None"] = relationship(
        "Employee",
        remote_side="Employee.id",
        foreign_keys=[manager_id],
        back_populates="direct_reports",
    )
    direct_reports: Mapped[list["Employee"]] = relationship(
        "Employee",
        foreign_keys=[manager_id],
        back_populates="manager",
    )
