"""Cross-version TOML loader.

Python 3.11+ ships :mod:`tomllib` in the standard library; on 3.10 we fall
back to the third-party :mod:`tomli` package (declared as a conditional
dependency in ``pyproject.toml``). This module exposes a single
``loads`` / ``load`` API plus the matching ``TOMLDecodeError`` so callers
can stay agnostic of the Python version.
"""

from __future__ import annotations

import sys
from typing import Any, BinaryIO

if sys.version_info >= (3, 11):
    import tomllib as _toml
else:  # pragma: no cover - exercised on Python 3.10 only
    import tomli as _toml

TOMLDecodeError = _toml.TOMLDecodeError
"""The decode-error type raised by :func:`loads` / :func:`load`."""


def loads(text: str) -> dict[str, Any]:
    """Parse a TOML *text* string into a dict.

    Raises :class:`TOMLDecodeError` on malformed input.
    """
    return _toml.loads(text)


def load(fp: BinaryIO) -> dict[str, Any]:
    """Parse TOML content from a binary file-like object."""
    return _toml.load(fp)


__all__ = ["TOMLDecodeError", "load", "loads"]
