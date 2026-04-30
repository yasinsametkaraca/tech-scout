"""Slug generation for run IDs and folder names.

Two slug flavors:

* :func:`slugify_topic` — topic title → folder slug (used by skill output)
* :func:`unique_run_slug` — short random ID for a run (used inside RunId)

Both are deterministic and safe for use in filesystem paths on Windows,
macOS, and Linux. Turkish characters (ş, ğ, ı, ç, ü, ö) are transliterated.
"""

from __future__ import annotations

import secrets
import string
from datetime import date

from slugify import slugify

from tech_scout.domain.value_objects import RunId, Slug

_RUN_SLUG_LEN = 8
_RUN_SLUG_ALPHABET = string.ascii_lowercase + string.digits


def slugify_topic(topic: str, *, max_length: int = 50) -> Slug:
    """Turn a free-form topic into a folder-safe slug.

    Examples::

        slugify_topic("MCP — Model Context Protocol")  -> "mcp-model-context-protocol"
        slugify_topic("Şirket içi gözlemleme")          -> "sirket-ici-gozlemleme"

    Raises :class:`ValueError` if the input has no extractable letters.
    """
    if not topic or not topic.strip():
        msg = "Cannot slugify empty topic"
        raise ValueError(msg)

    raw = slugify(
        topic,
        max_length=max_length,
        word_boundary=True,
        save_order=True,
        separator="-",
        lowercase=True,
    )
    if not raw:
        msg = f"Topic produced empty slug: {topic!r}"
        raise ValueError(msg)
    return Slug(value=raw)


def unique_run_slug(*, length: int = _RUN_SLUG_LEN) -> str:
    """Generate a short random slug suffix for use in a :class:`RunId`."""
    if not 6 <= length <= 12:
        msg = f"Run slug length must be 6-12: got {length}"
        raise ValueError(msg)
    return "".join(secrets.choice(_RUN_SLUG_ALPHABET) for _ in range(length))


def build_run_id(*, today: date | None = None, length: int = _RUN_SLUG_LEN) -> RunId:
    """Compose a fresh ``YYYY-MM-DD-<slug>`` :class:`RunId`."""
    d = today if today is not None else date.today()
    return RunId(value=f"{d.isoformat()}-{unique_run_slug(length=length)}")


def build_output_folder_name(*, today: date | None = None, topic_slug: Slug | str) -> str:
    """Compose ``YYYY-MM-DD-<topic-slug>`` for a package output folder."""
    d = today if today is not None else date.today()
    slug_str = topic_slug.value if isinstance(topic_slug, Slug) else str(topic_slug)
    return f"{d.isoformat()}-{slug_str}"
