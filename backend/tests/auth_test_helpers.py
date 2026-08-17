"""Test helper: register + assign a role, and return an auth header."""

from sqlalchemy.orm import Session

from app.core.security import create_token
from app.services.auth_service import AuthService


def auth_header_for_role(db_session: Session, *, role: str, email: str) -> dict[str, str]:
    user = AuthService(db_session).register(
        email=email, password="correct-horse-1", default_role=role
    )
    db_session.flush()
    token = create_token(str(user.id), "access")
    return {"Authorization": f"Bearer {token}"}
