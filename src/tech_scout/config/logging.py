"""Structured logging configuration via structlog.

By default emits JSON to stderr. Set ``TECH_SCOUT_LOG_FORMAT=console`` in
development for a human-readable format. Levels follow stdlib (DEBUG, INFO,
WARNING, ERROR, CRITICAL).

Usage::

    from tech_scout.config.logging import get_logger

    log = get_logger(__name__)
    log.info("scan_started", path="/tmp/x", reader_count=4)
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import BoundLogger
from structlog.types import EventDict, Processor

_CONFIGURED = False


def _add_log_level(_: object, method_name: str, event_dict: EventDict) -> EventDict:
    event_dict["level"] = method_name.upper()
    return event_dict


def _drop_color_message(_: object, __: str, event_dict: EventDict) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(
    *,
    level: str = "INFO",
    fmt: str = "json",
    log_file: str | None = None,
) -> None:
    """Configure structlog and the stdlib root logger.

    Idempotent: calling twice is safe. The first call wins; subsequent calls
    are no-ops to avoid duplicate handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    numeric_level = logging.getLevelName(level.upper())
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    handler: logging.Handler
    if log_file:
        handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(numeric_level)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_log_level,
        _drop_color_message,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    renderer: Processor
    if fmt == "console":
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    else:
        renderer = structlog.processors.JSONRenderer(sort_keys=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(name: str | None = None) -> BoundLogger:
    """Return a configured structlog logger.

    Calls :func:`configure_logging` with defaults if not already configured.
    Pass ``__name__`` so log entries carry the calling module.
    """
    if not _CONFIGURED:
        configure_logging()
    logger: BoundLogger = structlog.get_logger(name)
    return logger


def bind_context(**kwargs: Any) -> None:
    """Bind keys to all subsequent log entries in this thread/task."""
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """Remove keys from the bound context."""
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all bound context (test helper)."""
    structlog.contextvars.clear_contextvars()
