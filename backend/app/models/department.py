"""Department entity."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "employees.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_departments_manager_id",
        )
    )

    manager: Mapped["Employee | None"] = relationship(  # noqa: F821
        "Employee", foreign_keys=[manager_id], viewonly=True
    )
    employees: Mapped[list["Employee"]] = relationship(  # noqa: F821
        "Employee",
        foreign_keys="Employee.department_id",
        back_populates="department",
    )
