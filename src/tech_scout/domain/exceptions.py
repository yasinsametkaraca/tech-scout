"""Domain exception hierarchy.

All errors raised from `src/tech_scout/` derive from :class:`TechScoutError`.
Helper scripts catch these and convert to a JSON error envelope on stdout.
Each subclass declares a stable ``error_code`` (see
:mod:`tech_scout.domain.error_codes`) that callers may switch on; the
class name (``error_type``) is included for debugging only and is not a
contract.
"""

from __future__ import annotations

from typing import Any, ClassVar

from tech_scout.domain import error_codes


class TechScoutError(Exception):
    """Base class for all tech-scout domain errors.

    Carries an optional ``context`` mapping that gets serialized into
    structured error envelopes by the CLI layer.
    """

    error_code: ClassVar[str] = error_codes.INTERNAL_ERROR
    """Stable string identifier — see :mod:`tech_scout.domain.error_codes`."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "error_type": type(self).__name__,
            "message": self.message,
            "context": self.context,
        }


class CodebaseScanError(TechScoutError):
    """Raised when codebase scanning fails (unreadable path, malformed manifest)."""

    error_code: ClassVar[str] = error_codes.CODEBASE_SCAN_FAILED


class HistoryLookupError(TechScoutError):
    """Raised when listing or reading prior research runs fails."""

    error_code: ClassVar[str] = error_codes.HISTORY_LOOKUP_FAILED


class StateStoreError(TechScoutError):
    """Raised when reading/writing run-state files fails."""

    error_code: ClassVar[str] = error_codes.STATE_STORE_ERROR


class TemplateRenderError(TechScoutError):
    """Raised when Jinja2 template rendering fails or input data is incomplete."""

    error_code: ClassVar[str] = error_codes.TEMPLATE_RENDER_FAILED


class ValidationError(TechScoutError):
    """Raised when Phase 6 quality checks fail on a generated package."""

    error_code: ClassVar[str] = error_codes.PACKAGE_VALIDATION_FAILED


class ConfigurationError(TechScoutError):
    """Raised when configuration (settings, env) is invalid or missing."""

    error_code: ClassVar[str] = error_codes.CONFIGURATION_INVALID


class LocaleNotFoundError(TechScoutError):
    """Raised when a requested locale code or alias is not registered."""

    error_code: ClassVar[str] = error_codes.LOCALE_NOT_FOUND
