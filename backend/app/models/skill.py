"""Skill catalog and per-employee proficiency."""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"
    __table_args__ = (
        CheckConstraint(
            "proficiency_level BETWEEN 1 AND 5", name="ck_employee_skills_proficiency_range"
        ),
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    employee: Mapped["Employee"] = relationship("Employee")  # noqa: F821
    skill: Mapped["Skill"] = relationship("Skill")
