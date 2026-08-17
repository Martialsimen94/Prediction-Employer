"""Employee absences (sick leave, vacation, unpaid leave, other)."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import AbsenceType

if TYPE_CHECKING:
    from app.models.employee import Employee


class Absence(TimestampMixin, Base):
    __tablename__ = "absences"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_absences_end_after_start"),
        Index("ix_absences_employee_id", "employee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    absence_type: Mapped[AbsenceType] = mapped_column(
        pg_enum(AbsenceType, "absence_type"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    employee: Mapped["Employee"] = relationship("Employee")  # noqa: F821
