"""``ts-load-candidates`` — return saved Phase 3 output for resume."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn

from tech_scout.cli._common import parse_path, run_script
from tech_scout.domain.exceptions import StateStoreError
from tech_scout.observability import bind_run_id
from tech_scout.state import StateStore


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts-load-candidates",
        description="Load saved Phase 3 candidates for a run.",
    )
    p.add_argument("--run-id", required=True)
    p.add_argument("--output-folder", type=parse_path, required=True)
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()
    bind_run_id(args.run_id)

    store = StateStore(args.output_folder, args.run_id)
    candidates = store.read_candidates()
    if candidates is None:
        raise StateStoreError(
            "No candidates saved for this run",
            context={"run_id": args.run_id, "output_folder": str(args.output_folder)},
        )

    return {
        "run_id": args.run_id,
        "candidates": json.loads(candidates.model_dump_json()),
        "candidate_count": len(candidates.candidates),
        "candidate_ids": [c.id for c in candidates.candidates],
    }


def entry_point() -> NoReturn:
    if "--help" in sys.argv or "-h" in sys.argv:
        _build_parser().print_help()
        raise SystemExit(0)
    run_script(main)


if __name__ == "__main__":  # pragma: no cover
    entry_point()
