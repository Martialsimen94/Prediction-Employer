"""Registration, authentication and token issuance."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, verify_password
from app.models.auth import User
from app.repositories.user_repository import UserRepository

DEFAULT_ROLE = "employee"


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)

    def register(self, *, email: str, password: str, default_role: str = DEFAULT_ROLE) -> User:
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(email)

        user = self._users.create(email=email, hashed_password=hash_password(password))
        role = self._users.get_role_by_name(default_role)
        if role is not None:
            user.roles.append(role)
        self._session.flush()
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError

        user.last_login_at = datetime.now(UTC)
        self._session.flush()
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_token(str(user.id), "access"),
            refresh_token=create_token(str(user.id), "refresh"),
        )
