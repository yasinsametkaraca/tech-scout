"""Thin shim — delegates to :mod:`tech_scout.cli.load_candidates`."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tech_scout.cli.load_candidates import entry_point  # noqa: E402

if __name__ == "__main__":
    entry_point()
