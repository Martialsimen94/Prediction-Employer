"""Historized salary records — one row per compensation change, one open row per employee."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import SalaryChangeReason

if TYPE_CHECKING:
    from app.models.employee import Employee


class Salary(TimestampMixin, Base):
    __tablename__ = "salaries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_salaries_amount_positive"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= effective_date",
            name="ck_salaries_end_after_effective",
        ),
        Index("ix_salaries_employee_id", "employee_id"),
        Index(
            "ux_salaries_one_current_per_employee",
            "employee_id",
            unique=True,
            postgresql_where=text("end_date IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[SalaryChangeReason] = mapped_column(
        pg_enum(SalaryChangeReason, "salary_change_reason"), nullable=False
    )

    employee: Mapped["Employee"] = relationship("Employee")  # noqa: F821
