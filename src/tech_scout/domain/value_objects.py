"""Value objects — small immutable types with validation rules.

Value objects encode invariants that should be enforced at the boundary,
so the rest of the codebase can rely on the type itself rather than
re-validating defensively.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)

_RUN_ID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]{6,12}$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _ensure_writable_or_creatable_directory(value: Path) -> Path:
    if value.exists() and not value.is_dir():
        msg = f"Path exists but is not a directory: {value}"
        raise ValueError(msg)
    return value


WritableDirectory = Annotated[Path, AfterValidator(_ensure_writable_or_creatable_directory)]
"""A path validator that requires a directory that exists or can be created."""


class RunId(BaseModel):
    """Unique identifier for a research run.

    Format: ``YYYY-MM-DD-<slug>`` where slug is 6-12 lowercase alphanumerics.
    Example: ``2026-04-29-abc123``.
    """

    model_config = ConfigDict(frozen=True)

    value: str = Field(..., min_length=15, max_length=30)

    @field_validator("value")
    @classmethod
    def _check_format(cls, v: str) -> str:
        if not _RUN_ID_PATTERN.match(v):
            msg = (
                f"RunId must match pattern YYYY-MM-DD-<slug>: got {v!r}. "
                "The slug must be 6-12 lowercase alphanumerics."
            )
            raise ValueError(msg)
        return v

    @property
    def date_part(self) -> date:
        return datetime.strptime(self.value[:10], "%Y-%m-%d").date()

    @property
    def slug_part(self) -> str:
        return self.value[11:]

    def __str__(self) -> str:
        return self.value


class TimeWindow(BaseModel):
    """A closed-open time interval used to scope discovery."""

    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime

    @field_validator("end")
    @classmethod
    def _end_after_start(cls, v: datetime, info: Any) -> datetime:
        start = info.data.get("start") if hasattr(info, "data") else None
        if start is not None and v <= start:
            msg = f"TimeWindow end must be after start: start={start}, end={v}"
            raise ValueError(msg)
        return v

    @classmethod
    def last_n_days(cls, days: int, *, now: datetime | None = None) -> TimeWindow:
        end = now if now is not None else datetime.now()
        start = end.replace(microsecond=0) - _days_delta(days)
        return cls(start=start, end=end.replace(microsecond=0))

    def days(self) -> int:
        return (self.end - self.start).days


def _days_delta(days: int) -> Any:
    from datetime import timedelta

    return timedelta(days=days)


class SourceRef(BaseModel):
    """A reference to a source — paper, blog post, repo, product page."""

    model_config = ConfigDict(frozen=True)

    url: HttpUrl
    title: str = Field(..., min_length=1, max_length=500)
    publication_date: date | None = None
    publisher: str | None = Field(default=None, max_length=200)


class OutputPath(BaseModel):
    """Validated output folder for a research package.

    Either points to an existing directory or to a path whose parent exists
    (so we can create it).
    """

    model_config = ConfigDict(frozen=True)

    path: WritableDirectory

    @field_validator("path")
    @classmethod
    def _parent_must_exist_if_path_does_not(cls, v: Path) -> Path:
        if not v.exists() and not v.parent.exists():
            msg = f"Parent of output path does not exist: {v.parent}"
            raise ValueError(msg)
        return v


class Slug(BaseModel):
    """A folder/url-safe slug derived from a topic."""

    model_config = ConfigDict(frozen=True)

    value: str = Field(..., min_length=1, max_length=80)

    @field_validator("value")
    @classmethod
    def _check_format(cls, v: str) -> str:
        if not _SLUG_PATTERN.match(v):
            msg = f"Slug must be lowercase alphanumeric with single hyphens: got {v!r}"
            raise ValueError(msg)
        return v

    def __str__(self) -> str:
        return self.value
