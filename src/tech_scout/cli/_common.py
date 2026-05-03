"""Shared CLI infrastructure.

The CLI envelope is the contract between helper commands and the skill —
see :doc:`/cli-contract`. Versioned so we can evolve it safely.

This module deliberately does not call :func:`sys.path` shimming: the
package is importable through normal means (``pip install`` or the
``src/`` layout used during development). The legacy ``scripts/ts_*.py``
shims handle source-checkout bootstrapping themselves.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final, NoReturn

from tech_scout.config.logging import configure_logging
from tech_scout.domain import error_codes
from tech_scout.domain.exceptions import TechScoutError

ENVELOPE_VERSION: Final[int] = 1
"""Bump on backwards-incompatible envelope shape changes.

See ``docs/cli-contract.md`` for the full specification.
"""


def ensure_utf8_streams() -> None:
    """Force stdout/stderr to UTF-8 so non-ASCII output works on Windows.

    Default Windows console encoding (e.g. cp1254 in Turkish locales)
    cannot encode em-dashes, arrows, Turkish-specific punctuation, etc.
    The skill expects clean JSON envelopes regardless of locale, so we
    reconfigure early. Safe no-op on Linux/macOS where UTF-8 is already
    default.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def emit_success(data: dict[str, Any], *, exit_code: int = 0) -> NoReturn:
    """Print a versioned success envelope to stdout and exit cleanly."""
    envelope = {
        "envelope_version": ENVELOPE_VERSION,
        "status": "ok",
        "data": data,
    }
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    sys.stdout.flush()
    raise SystemExit(exit_code)


def emit_error(
    error: TechScoutError | Exception,
    *,
    exit_code: int = 1,
    error_code: str | None = None,
) -> NoReturn:
    """Print a structured error envelope and exit non-zero."""
    if isinstance(error, TechScoutError):
        body: dict[str, Any] = error.to_dict()
        if error_code is not None:
            body["error_code"] = error_code
    else:
        body = {
            "error_code": error_code or error_codes.INTERNAL_ERROR,
            "error_type": type(error).__name__,
            "message": str(error),
            "context": {},
        }
    envelope = {
        "envelope_version": ENVELOPE_VERSION,
        "status": "error",
        "data": body,
    }
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    sys.stdout.flush()
    raise SystemExit(exit_code)


def run_script(main_func: Callable[[], dict[str, Any]]) -> NoReturn:
    """Run *main_func* and emit the standard envelope on its outcome.

    Translates exceptions to the right envelope shape:

    * :class:`tech_scout.domain.exceptions.TechScoutError` → that error's
      declared ``error_code`` and exit code 1.
    * :class:`KeyboardInterrupt` → ``USER_INTERRUPTED``, exit code 130.
    * Anything else → ``INTERNAL_ERROR``, exit code 2.

    Always exits the process — never returns.
    """
    ensure_utf8_streams()
    configure_logging(level="INFO", fmt="json")
    try:
        result = main_func()
    except TechScoutError as e:
        emit_error(e, exit_code=1)
    except KeyboardInterrupt as e:
        emit_error(
            RuntimeError("Interrupted by user"),
            exit_code=130,
            error_code=error_codes.USER_INTERRUPTED,
        )
        raise SystemExit(130) from e  # pragma: no cover
    except Exception as e:
        emit_error(e, exit_code=2, error_code=error_codes.INTERNAL_ERROR)
    else:
        emit_success(result)


def parse_path(raw: str) -> Path:
    """Convert a CLI string to an expanded, resolved Path."""
    return Path(raw).expanduser().resolve()


def repo_root() -> Path:
    """Return the project root (where ``pyproject.toml`` lives).

    Walks up from this file until ``pyproject.toml`` is found. When the
    package is pip-installed, no ``pyproject.toml`` is present in any
    parent — in that case we return the user's current working directory
    so callers fall back to a sensible default.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path.cwd()


__all__ = [
    "ENVELOPE_VERSION",
    "emit_error",
    "emit_success",
    "ensure_utf8_streams",
    "parse_path",
    "repo_root",
    "run_script",
]
