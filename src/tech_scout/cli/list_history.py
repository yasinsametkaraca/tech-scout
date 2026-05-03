"""``ts-list-history`` — list past research run folders (newest first)."""

from __future__ import annotations

import argparse
import sys
from typing import Any, NoReturn

from tech_scout.cli._common import parse_path, run_script
from tech_scout.history import HistoryRepository


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts-list-history",
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


def entry_point() -> NoReturn:
    if "--help" in sys.argv or "-h" in sys.argv:
        _build_parser().print_help()
        raise SystemExit(0)
    run_script(main)


if __name__ == "__main__":  # pragma: no cover
    entry_point()
