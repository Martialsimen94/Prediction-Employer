"""Shared SQLAlchemy declarative base and reusable mixins."""

from datetime import datetime
from enum import StrEnum
from typing import TypeVar

from sqlalchemy import DateTime, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

E = TypeVar("E", bound=StrEnum)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def pg_enum(enum_cls: type[E], name: str) -> SqlEnum:
    """Build a native Postgres ENUM column type storing each member's *value*
    (e.g. "active") rather than SQLAlchemy's default of its *name*
    (e.g. "ACTIVE"), so the DB representation matches the StrEnum value used
    everywhere else (Pydantic schemas, JSON API payloads, raw SQL views)."""
    return SqlEnum(
        enum_cls, name=name, native_enum=True, values_callable=lambda obj: [e.value for e in obj]
    )


class TimestampMixin:
    """Adds `created_at` / `updated_at` audit columns, maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
