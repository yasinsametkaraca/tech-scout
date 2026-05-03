"""Thin shim — delegates to :mod:`tech_scout.cli.doctor`.

Kept so the repo's ``python scripts/ts_doctor.py`` invocation pattern (used
by the Claude Code skill and the legacy Make targets) keeps working. The
real logic lives in the installable ``tech_scout`` package; the shim
inserts ``src/`` onto ``sys.path`` for source-checkout use and forwards
to :func:`tech_scout.cli.doctor.entry_point`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tech_scout.cli.doctor import entry_point  # noqa: E402

if __name__ == "__main__":
    entry_point()
