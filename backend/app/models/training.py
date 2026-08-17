"""Training catalog and per-employee enrollment/completion tracking."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import TrainingStatus

if TYPE_CHECKING:
    from app.models.employee import Employee


class Training(TimestampMixin, Base):
    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(150))
    category: Mapped[str | None] = mapped_column(String(100))
    duration_hours: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class EmployeeTraining(TimestampMixin, Base):
    __tablename__ = "employee_trainings"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "training_id", "start_date", name="uq_employee_training_enrollment"
        ),
        Index("ix_employee_trainings_employee_id", "employee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id", ondelete="CASCADE"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    completion_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[TrainingStatus] = mapped_column(
        pg_enum(TrainingStatus, "training_status"),
        default=TrainingStatus.ENROLLED,
        nullable=False,
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    employee: Mapped["Employee"] = relationship("Employee")  # noqa: F821
    training: Mapped["Training"] = relationship("Training")
