"""Promotion history — job title and/or department changes."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class Promotion(TimestampMixin, Base):
    __tablename__ = "promotions"
    __table_args__ = (Index("ix_promotions_employee_id", "employee_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    previous_job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    new_job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    previous_department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    new_department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    promotion_date: Mapped[date] = mapped_column(Date, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))

    employee: Mapped["Employee"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[employee_id]
    )
    approver: Mapped["Employee | None"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[approved_by]
    )
