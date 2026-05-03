"""Stable, machine-friendly error codes for the helper-script CLI envelope.

The skill (and any other consumer of the helper scripts) parses the JSON
envelope on stdout and dispatches on ``error_code``. Class names
(``error_type``) are kept for backwards compatibility but are *not* a
contract: refactoring a class name must never break callers. The
``error_code`` strings below are the contract.

Every :class:`tech_scout.domain.exceptions.TechScoutError` subclass that
the CLI may surface declares its ``error_code`` as a class attribute. The
codes here form a small, finite set so callers can switch on them in a
``match`` statement.
"""

from __future__ import annotations

from typing import Final

# Generic / unexpected
INTERNAL_ERROR: Final[str] = "INTERNAL_ERROR"
"""Catch-all for unhandled exceptions outside the domain hierarchy."""

USER_INTERRUPTED: Final[str] = "USER_INTERRUPTED"
"""Raised when the helper is killed by ``Ctrl+C`` (SIGINT)."""

# Domain errors
CONFIGURATION_INVALID: Final[str] = "CONFIGURATION_INVALID"
"""Settings or environment misconfigured (missing dir, bad locale, etc.)."""

LOCALE_NOT_FOUND: Final[str] = "LOCALE_NOT_FOUND"
"""The requested locale code or alias is not registered."""

CODEBASE_SCAN_FAILED: Final[str] = "CODEBASE_SCAN_FAILED"
"""Codebase scanner could not read or parse the input root."""

HISTORY_LOOKUP_FAILED: Final[str] = "HISTORY_LOOKUP_FAILED"
"""History repository could not enumerate prior runs."""

STATE_STORE_ERROR: Final[str] = "STATE_STORE_ERROR"
"""State file read/write/parse failed."""

TEMPLATE_RENDER_FAILED: Final[str] = "TEMPLATE_RENDER_FAILED"
"""Jinja2 template render failed (missing variable, missing template, …)."""

PACKAGE_VALIDATION_FAILED: Final[str] = "PACKAGE_VALIDATION_FAILED"
"""Phase 6 package validator returned errors or missing documents."""


ALL_CODES: Final[frozenset[str]] = frozenset(
    {
        INTERNAL_ERROR,
        USER_INTERRUPTED,
        CONFIGURATION_INVALID,
        LOCALE_NOT_FOUND,
        CODEBASE_SCAN_FAILED,
        HISTORY_LOOKUP_FAILED,
        STATE_STORE_ERROR,
        TEMPLATE_RENDER_FAILED,
        PACKAGE_VALIDATION_FAILED,
    }
)
"""Every error code defined here, for use in tests or registry checks."""


__all__ = [
    "ALL_CODES",
    "CODEBASE_SCAN_FAILED",
    "CONFIGURATION_INVALID",
    "HISTORY_LOOKUP_FAILED",
    "INTERNAL_ERROR",
    "LOCALE_NOT_FOUND",
    "PACKAGE_VALIDATION_FAILED",
    "STATE_STORE_ERROR",
    "TEMPLATE_RENDER_FAILED",
    "USER_INTERRUPTED",
]
