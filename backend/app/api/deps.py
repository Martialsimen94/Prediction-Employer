"""Shared FastAPI dependencies: DB session, current user, RBAC checks."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import InvalidTokenError, decode_token
from app.models.auth import User
from app.repositories.user_repository import UserRepository

_settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{_settings.api_v1_prefix}/auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except InvalidTokenError:
        raise _CREDENTIALS_ERROR from None

    if payload.get("type") != "access":
        raise _CREDENTIALS_ERROR

    user_id = payload.get("sub")
    if user_id is None:
        raise _CREDENTIALS_ERROR

    user = UserRepository(db).get_by_id(int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR

    return user


def require_permission(code: str) -> Callable[[User], User]:
    """Build a dependency that requires the current user to hold `code`
    through at least one of their roles."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        permission_codes = {
            permission.code for role in user.roles for permission in role.permissions
        }
        if code not in permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {code}"
            )
        return user

    return dependency
