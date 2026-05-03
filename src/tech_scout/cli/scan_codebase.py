"""``ts-scan-codebase`` — extract a tech-stack profile from a codebase."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn

from tech_scout.cli._common import parse_path, run_script
from tech_scout.codebase import scan_codebase
from tech_scout.domain.exceptions import CodebaseScanError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts-scan-codebase",
        description="Scan a codebase and produce a CodebaseProfile JSON document.",
    )
    p.add_argument("root", type=parse_path, help="Path to the codebase root directory")
    p.add_argument(
        "--output",
        type=parse_path,
        help="Optional path to also write the JSON profile to (in addition to stdout)",
    )
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()

    if not args.root.exists():
        raise CodebaseScanError(
            f"Codebase root does not exist: {args.root}",
            context={"root": str(args.root)},
        )

    profile = scan_codebase(args.root)
    profile_data = json.loads(profile.model_dump_json())

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            profile.model_dump_json(indent=2),
            encoding="utf-8",
        )

    return {
        "root_path": str(profile.root_path),
        "profile": profile_data,
        "summary": {
            "entry_count": len(profile.entries),
            "manifest_count": len(profile.manifest_files_found),
            "primary_languages": [e.name for e in profile.primary_languages()],
            "has_multi_agent": profile.architecture.has_multi_agent,
            "pattern": profile.architecture.pattern,
        },
    }


def entry_point() -> NoReturn:
    if "--help" in sys.argv or "-h" in sys.argv:
        _build_parser().print_help()
        raise SystemExit(0)
    run_script(main)


if __name__ == "__main__":  # pragma: no cover
    entry_point()
