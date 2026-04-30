"""Shared utilities for helper scripts.

Helper scripts share a few concerns:

* Resolve the project root and add ``src/`` to ``sys.path`` (so they work
  whether installed as a package or run directly from a checkout).
* Emit JSON envelopes for both success and error cases so the skill can
  parse a single, consistent shape.
* Configure structlog with sensible defaults.

This module exposes a tiny API used by every script under ``scripts/``.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

# --------------------------------------------------------------------------
# sys.path bootstrap (so scripts can be run as `python scripts/foo.py`)
# --------------------------------------------------------------------------


def bootstrap_sys_path() -> None:
    """Ensure ``src/`` is on sys.path so ``tech_scout`` imports work."""
    here = Path(__file__).resolve()
    project_root = here.parent.parent
    src = project_root / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _ensure_utf8_streams() -> None:
    """Force stdout/stderr to UTF-8 so non-ASCII output works on Windows.

    Default Windows console encoding (e.g. cp1254 in Turkish locales) cannot
    encode em-dashes, arrows, Turkish-specific punctuation, etc. The skill
    expects clean JSON envelopes regardless of locale, so we reconfigure
    early. Safe no-op on Linux/macOS where UTF-8 is already default.
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
            # Stream may already be detached or non-text — skip silently.
            continue


bootstrap_sys_path()
_ensure_utf8_streams()


# These imports rely on bootstrap above
from tech_scout.config.logging import configure_logging  # noqa: E402
from tech_scout.domain.exceptions import TechScoutError  # noqa: E402

# --------------------------------------------------------------------------
# JSON envelope contract
# --------------------------------------------------------------------------


def emit_success(data: dict[str, Any], *, exit_code: int = 0) -> NoReturn:
    """Print ``{"status": "ok", "data": ...}`` to stdout and exit cleanly.

    The skill parses a single JSON object from stdout. Stderr carries logs.
    """
    envelope = {"status": "ok", "data": data}
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    sys.stdout.flush()
    raise SystemExit(exit_code)


def emit_error(
    error: TechScoutError | Exception,
    *,
    exit_code: int = 1,
) -> NoReturn:
    """Print a structured error envelope and exit non-zero."""
    if isinstance(error, TechScoutError):
        body: dict[str, Any] = error.to_dict()
    else:
        body = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": {},
        }
    envelope = {"status": "error", "data": body}
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    sys.stdout.flush()
    raise SystemExit(exit_code)


# --------------------------------------------------------------------------
# Run-script wrapper
# --------------------------------------------------------------------------


def run_script(main_func: Callable[[], dict[str, Any]]) -> NoReturn:
    """Wrap a script's main into the standard envelope flow.

    Usage::

        def main() -> dict[str, object]:
            ...
            return {"some": "data"}

        if __name__ == "__main__":
            run_script(main)
    """
    configure_logging(level="INFO", fmt="json")
    try:
        result = main_func()
    except TechScoutError as e:
        emit_error(e)
    except KeyboardInterrupt:
        emit_error(
            RuntimeError("Interrupted by user"),
            exit_code=130,
        )
    except Exception as e:
        emit_error(e, exit_code=2)
    else:
        emit_success(result)


# --------------------------------------------------------------------------
# Shared argument helpers
# --------------------------------------------------------------------------


def parse_path(raw: str) -> Path:
    """Convert a CLI string to an expanded, resolved Path."""
    return Path(raw).expanduser().resolve()


def repo_root() -> Path:
    """Return the project root (where pyproject.toml lives)."""
    return Path(__file__).resolve().parent.parent
