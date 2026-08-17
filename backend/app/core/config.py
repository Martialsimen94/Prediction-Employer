"""Application configuration, loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root, regardless of the process's cwd (repo_root/backend/app/core/config.py).
_REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Central application settings, sourced from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False

    project_name: str = "AI Employee Retention Platform"
    api_v1_prefix: str = "/api/v1"

    postgres_dsn: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/retention_platform"
    )
    redis_dsn: str = Field(default="redis://localhost:6379/0")

    jwt_secret_key: str = "changeme-in-env"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    mlflow_tracking_uri: str = "http://localhost:5000"

    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one per process)."""
    return Settings()
