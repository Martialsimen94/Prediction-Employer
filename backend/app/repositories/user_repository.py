"""Data access for users and roles."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import Role, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        return self._session.scalar(select(User).where(User.email == email))

    def get_by_id(self, user_id: int) -> User | None:
        return self._session.get(User, user_id)

    def create(self, *, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        self._session.add(user)
        self._session.flush()
        return user

    def get_role_by_name(self, name: str) -> Role | None:
        return self._session.scalar(select(Role).where(Role.name == name))
