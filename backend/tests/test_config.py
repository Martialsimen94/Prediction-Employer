"""Sanity tests for application configuration loading."""

from app.core.config import Settings, get_settings


def test_settings_default_values() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.project_name == "AI Employee Retention Platform"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.environment == "development"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
