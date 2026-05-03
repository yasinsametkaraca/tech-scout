"""Settings loaded from environment and ``.env``.

Settings have safe defaults so the app runs out of the box without any user
configuration. Override via environment variables (``TECH_SCOUT_*``) or a
``.env`` file at the repository root. See ``.env.example`` for common
overrides.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tech_scout.domain.exceptions import LocaleNotFoundError
from tech_scout.locales.registry import DEFAULT_LOCALE_CODE, get_locale


def _repo_root() -> Path:
    """Return the repository root (where pyproject.toml lives).

    Walks up from this file until a ``pyproject.toml`` is found. When the
    package is pip-installed, no ``pyproject.toml`` is present in any
    parent of ``site-packages``; in that case we fall back to the
    package's parent directory. Code that needs the bundled templates
    must use :func:`tech_scout.output.template_assets.packaged_templates_root`
    rather than rebuilding a path from the repo root.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return here.parent.parent.parent


_REPO_ROOT = _repo_root()
_DEFAULT_OUTPUT_ROOT = Path.home() / "tech-scout-runs"


def _default_templates_dir() -> Path:
    """Resolve the default templates directory across install modes.

    Lazy import — :mod:`tech_scout.output` is heavier than :mod:`config`
    and we want ``Settings`` instantiation to stay cheap. The function is
    called once at field-default time per process.
    """
    from tech_scout.output.template_assets import packaged_templates_root

    return packaged_templates_root()


class Settings(BaseSettings):
    """Application settings.

    All fields can be overridden via environment variables prefixed with
    ``TECH_SCOUT_`` or in a ``.env`` file at the repo root. Defaults aim
    to be portable across operating systems; see ``.env.example`` for the
    common overrides (output root, default locale, log format/level).
    """

    model_config = SettingsConfigDict(
        env_prefix="TECH_SCOUT_",
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Paths ---

    repo_root: Path = Field(default=_REPO_ROOT)
    templates_dir: Path = Field(default_factory=_default_templates_dir)
    scripts_dir: Path = Field(default=_REPO_ROOT / "scripts")
    skill_reference_dir: Path = Field(
        default=_REPO_ROOT / ".claude" / "skills" / "tech-scout" / "reference"
    )
    default_output_root: Path = Field(default=_DEFAULT_OUTPUT_ROOT)

    # --- Behavior ---

    max_findings_per_run: int = Field(default=50, ge=10, le=200)
    min_candidates: int = Field(default=8, ge=3, le=20)
    max_candidates: int = Field(default=12, ge=3, le=20)
    default_time_window_days: int = Field(default=7, ge=1, le=90)
    state_subdir_name: str = Field(default=".tech-scout")

    # --- Logging ---

    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json", pattern=r"^(json|console)$")
    log_file: Path | None = None

    # --- Locale ---

    default_locale_code: str = Field(default=DEFAULT_LOCALE_CODE, pattern=r"^[a-z]{2,16}$")

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, v: str) -> str:
        normalized = v.upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in valid:
            msg = f"log_level must be one of {sorted(valid)}, got {v!r}"
            raise ValueError(msg)
        return normalized

    @field_validator("default_locale_code")
    @classmethod
    def _validate_locale_code_registered(cls, v: str) -> str:
        # Resolves alias → canonical code, and rejects unknown values.
        try:
            spec = get_locale(v)
        except LocaleNotFoundError as exc:
            # Translate to ValueError so Pydantic wraps it into ValidationError.
            raise ValueError(str(exc)) from exc
        return spec.code

    @model_validator(mode="after")
    def _check_candidate_bounds(self) -> Settings:
        if self.max_candidates < self.min_candidates:
            msg = (
                f"max_candidates ({self.max_candidates}) must be "
                f">= min_candidates ({self.min_candidates})"
            )
            raise ValueError(msg)
        return self

    def resolve_output_root(self, override: Path | None = None) -> Path:
        return override if override is not None else self.default_output_root


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance.

    Use this in helper scripts and library code instead of constructing
    :class:`Settings` directly. The cache is global per process; call
    :func:`reset_settings_cache` from tests if you need to override.
    """
    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings (test-only helper)."""
    get_settings.cache_clear()


def settings_from_env_overrides(**overrides: object) -> Settings:
    """Build a Settings instance from explicit overrides.

    Used by tests to supply non-default values without touching env vars.
    Unknown fields raise — Settings has ``extra='ignore'`` for env, but
    here we want explicit failure to catch typos.
    """
    return Settings.model_validate(overrides)


def env_or_default(name: str, default: str) -> str:
    """Tiny helper for reading raw env vars when full Settings is overkill."""
    return os.environ.get(name, default)
