"""Domain exception hierarchy.

All errors raised from `src/tech_scout/` derive from :class:`TechScoutError`.
Helper scripts catch these and convert to a JSON error envelope on stdout.
"""

from __future__ import annotations

from typing import Any


class TechScoutError(Exception):
    """Base class for all tech-scout domain errors.

    Carries an optional ``context`` mapping that gets serialized into
    structured error envelopes by the CLI layer.
    """

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "context": self.context,
        }


class CodebaseScanError(TechScoutError):
    """Raised when codebase scanning fails (unreadable path, malformed manifest)."""


class HistoryLookupError(TechScoutError):
    """Raised when listing or reading prior research runs fails."""


class StateStoreError(TechScoutError):
    """Raised when reading/writing run-state files fails."""


class TemplateRenderError(TechScoutError):
    """Raised when Jinja2 template rendering fails or input data is incomplete."""


class ValidationError(TechScoutError):
    """Raised when Phase 6 quality checks fail on a generated package."""


class ConfigurationError(TechScoutError):
    """Raised when configuration (settings, env) is invalid or missing."""


class LocaleNotFoundError(TechScoutError):
    """Raised when a requested locale code or alias is not registered."""
