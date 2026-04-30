"""tech-scout list-history — list past research run folders.

Usage::

    python scripts/ts_list_history.py <history-root>

Output: JSON envelope with an array of past entries (newest first).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import emit_error, emit_success, parse_path
from tech_scout.history import HistoryRepository


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts_list_history",
        description="List past research run folders (newest first).",
    )
    p.add_argument("root", type=parse_path, help="Path to the research-documentation root")
    p.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of entries to return (default: 20)",
    )
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()

    if not args.root.exists():
        return {"root": str(args.root), "entries": [], "total": 0}

    repo = HistoryRepository(args.root)
    entries = repo.list_entries()
    truncated = entries[: max(args.limit, 1)]

    serialized: list[dict[str, Any]] = []
    for e in truncated:
        serialized.append(
            {
                "folder_path": str(e.folder_path),
                "folder_slug": e.folder_slug,
                "title": e.title,
                "primary_topic": e.primary_topic,
                "completed_date": e.completed_date.isoformat() if e.completed_date else None,
            }
        )

    return {
        "root": str(args.root),
        "entries": serialized,
        "total": len(entries),
        "returned": len(serialized),
    }


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        _build_parser().print_help()
        sys.exit(0)
    try:
        emit_success(main())
    except SystemExit:
        raise
    except Exception as exc:
        emit_error(exc, exit_code=1)
