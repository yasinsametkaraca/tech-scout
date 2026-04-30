"""Correlation helpers — bind a run_id to all log entries from this thread.

Used by helper scripts so every structlog log entry carries the run_id of
the run they belong to, without each call site having to remember to
include it.
"""

from __future__ import annotations

from typing import Final

import structlog

_RUN_ID_KEY: Final[str] = "run_id"


def bind_run_id(run_id: str) -> None:
    """Bind *run_id* to all subsequent log entries in this thread/task."""
    structlog.contextvars.bind_contextvars(**{_RUN_ID_KEY: run_id})


def clear_run_id() -> None:
    """Remove the run_id from the bound context."""
    structlog.contextvars.unbind_contextvars(_RUN_ID_KEY)


def current_run_id() -> str | None:
    """Return the currently bound run_id, if any."""
    ctx = structlog.contextvars.get_contextvars()
    value = ctx.get(_RUN_ID_KEY)
    return str(value) if value is not None else None
