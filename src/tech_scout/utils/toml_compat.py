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
    # tomli is declared as a conditional dependency in pyproject.toml with
    # the env marker `python_version<'3.11'`, so on 3.11+ pip will not have
    # installed it. Mypy still type-checks this branch under the pinned
    # python_version=3.10 setting, so we suppress its missing-import error
    # both via `[tool.mypy.overrides]` and inline so a partial override
    # cannot regress the matrix.
    import tomli as _toml  # type: ignore[import-not-found, unused-ignore]

TOMLDecodeError = _toml.TOMLDecodeError
"""The decode-error type raised by :func:`loads` / :func:`load`."""


def loads(text: str) -> dict[str, Any]:
    """Parse a TOML *text* string into a dict.

    Raises :class:`TOMLDecodeError` on malformed input.
    """
    # The intermediate annotated assignment narrows the underlying call's
    # return type from Any (when tomli is treated as an untyped import on
    # Python 3.11+ matrix legs) to the public API's promised dict shape.
    result: dict[str, Any] = _toml.loads(text)
    return result


def load(fp: BinaryIO) -> dict[str, Any]:
    """Parse TOML content from a binary file-like object."""
    result: dict[str, Any] = _toml.load(fp)
    return result


__all__ = ["TOMLDecodeError", "load", "loads"]
