"""Cross-cutting utilities — small pure helpers used throughout the codebase.

This package must not depend on other internal packages (except domain).
It is the lowest-level "leaf" module so its functions can be reused
without circular imports.
"""

from __future__ import annotations

from tech_scout.utils.path_safety import (
    is_within_directory,
    normalize_path,
    safe_relative_path,
)
from tech_scout.utils.time import (
    iso_now,
    iso_today,
    parse_iso_date,
    parse_iso_datetime,
)

__all__ = [
    "is_within_directory",
    "iso_now",
    "iso_today",
    "normalize_path",
    "parse_iso_date",
    "parse_iso_datetime",
    "safe_relative_path",
]
