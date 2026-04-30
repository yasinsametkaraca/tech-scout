"""Configuration & logging setup.

The :mod:`config` package centralizes settings (read from environment and
``.env``) and structured logging configuration. Library and helper code
should import :func:`get_settings` and :func:`get_logger` from this package
rather than constructing them ad-hoc.
"""

from __future__ import annotations

from tech_scout.config.logging import configure_logging, get_logger
from tech_scout.config.settings import Settings, get_settings

__all__ = ["Settings", "configure_logging", "get_logger", "get_settings"]
