"""Unit tests for application settings."""

from __future__ import annotations

import pytest

from tech_scout.config.settings import (
    Settings,
    env_or_default,
    get_settings,
    reset_settings_cache,
    settings_from_env_overrides,
)


def setup_function() -> None:
    reset_settings_cache()


def test_get_settings_returns_singleton() -> None:
    a = get_settings()
    b = get_settings()
    assert a is b


def test_default_field_values() -> None:
    s = Settings()
    assert s.max_findings_per_run == 50
    assert s.min_candidates == 8
    assert s.max_candidates == 12
    assert s.default_time_window_days == 7
    assert s.log_level == "INFO"
    assert s.log_format == "json"
    assert s.default_locale_code == "en"


def test_default_locale_code_alias_is_normalized() -> None:
    s = Settings(default_locale_code="english")
    assert s.default_locale_code == "en"


def test_default_locale_code_unknown_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(default_locale_code="kk")


def test_log_level_normalized_to_upper() -> None:
    s = Settings(log_level="warning")
    assert s.log_level == "WARNING"


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(log_level="bogus")


def test_max_candidates_must_geq_min() -> None:
    with pytest.raises(ValueError):
        Settings(min_candidates=10, max_candidates=8)


def test_resolve_output_root_with_override(tmp_path) -> None:  # type: ignore[no-untyped-def]
    s = Settings()
    assert s.resolve_output_root(tmp_path) == tmp_path


def test_resolve_output_root_default() -> None:
    s = Settings()
    assert s.resolve_output_root(None) == s.default_output_root


def test_settings_from_env_overrides() -> None:
    s = settings_from_env_overrides(log_level="DEBUG", default_time_window_days=14)
    assert s.log_level == "DEBUG"
    assert s.default_time_window_days == 14


def test_env_or_default(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("TECH_SCOUT_TEST_VAR", "from_env")
    assert env_or_default("TECH_SCOUT_TEST_VAR", "fallback") == "from_env"
    monkeypatch.delenv("TECH_SCOUT_TEST_VAR", raising=False)
    assert env_or_default("TECH_SCOUT_TEST_VAR", "fallback") == "fallback"
