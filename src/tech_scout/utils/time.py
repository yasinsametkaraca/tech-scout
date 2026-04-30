"""Time utilities — ISO formatting and parsing.

Centralizes timestamp formatting so the codebase stays consistent and
serialization round-trips cleanly through JSON state files.
"""

from __future__ import annotations

from datetime import date, datetime, timezone


def iso_now(*, naive: bool = False) -> str:
    """Return the current time as ISO-8601 string.

    By default returns a UTC timestamp with timezone suffix (``Z``).
    Set ``naive=True`` to drop the timezone (useful for local timestamps).
    """
    now = datetime.now(tz=timezone.utc) if not naive else datetime.now()
    return now.replace(microsecond=0).isoformat()


def iso_today() -> str:
    """Return today's date as YYYY-MM-DD."""
    return date.today().isoformat()


def parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime string.

    Accepts both ``Z`` suffix and explicit ``+HH:MM`` offsets, plus naive
    forms. Raises :class:`ValueError` on malformed input.
    """
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def parse_iso_date(value: str) -> date:
    """Parse an ISO-8601 date string (YYYY-MM-DD)."""
    return date.fromisoformat(value.strip())


def humanize_minutes(minutes: int) -> str:
    """Convert minutes to a short human-readable string ('1h 30m', '45m')."""
    if minutes < 0:
        msg = f"minutes must be non-negative, got {minutes}"
        raise ValueError(msg)
    if minutes < 60:
        return f"{minutes}m"
    hours, remainder = divmod(minutes, 60)
    if remainder == 0:
        return f"{hours}h"
    return f"{hours}h {remainder}m"
