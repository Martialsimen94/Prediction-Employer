"""Periodic performance evaluations."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class PerformanceReview(TimestampMixin, Base):
    __tablename__ = "performance_reviews"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 5", name="ck_performance_reviews_score_range"),
        Index("ix_performance_reviews_employee_id", "employee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    review_period: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)

    employee: Mapped["Employee"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[employee_id]
    )
    reviewer: Mapped["Employee | None"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[reviewer_id]
    )
