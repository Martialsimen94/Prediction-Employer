"""Shared pytest fixtures for the backend test suite."""

from collections.abc import Generator

import pytest
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, engine


@pytest.fixture
def db_connection() -> Generator[Connection, None, None]:
    """A DB connection wrapped in a transaction that is always rolled back,
    so tests never leave data behind or interfere with one another. Skips
    the test if no database is reachable."""
    try:
        connection = engine.connect()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"database not reachable: {exc}")

    trans = connection.begin()
    try:
        yield connection
    finally:
        # A failed flush (e.g. an expected IntegrityError from a constraint
        # test) already deactivates the transaction; only roll back if it's
        # still active to avoid a harmless-but-noisy SAWarning.
        if trans.is_active:
            trans.rollback()
        connection.close()


@pytest.fixture
def db_session(db_connection: Connection) -> Generator[Session, None, None]:
    """An ORM session bound to the rolled-back-on-teardown `db_connection`."""
    session = SessionLocal(bind=db_connection)
    try:
        yield session
    finally:
        session.close()
