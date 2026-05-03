"""``ts-save-candidates`` — persist Phase 3 output to run state."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn

from tech_scout.cli._common import parse_path, run_script
from tech_scout.domain.exceptions import StateStoreError
from tech_scout.domain.models import CandidateList
from tech_scout.observability import AuditLogger, bind_run_id
from tech_scout.state import AUDIT_FILENAME, StateStore


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts-save-candidates",
        description="Persist a CandidateList JSON to run state.",
    )
    p.add_argument("--run-id", required=True)
    p.add_argument("--output-folder", type=parse_path, required=True)
    p.add_argument("--candidates-file", type=parse_path, required=True)
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()

    if not args.candidates_file.is_file():
        raise StateStoreError(
            f"Candidates file does not exist: {args.candidates_file}",
            context={"path": str(args.candidates_file)},
        )

    raw = args.candidates_file.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StateStoreError(
            f"Candidates file is not valid JSON: {args.candidates_file}",
            context={"path": str(args.candidates_file), "error": str(exc)},
        ) from exc

    candidates = CandidateList.model_validate(data)

    bind_run_id(args.run_id)
    store = StateStore(args.output_folder, args.run_id)
    store.initialize()
    saved_path = store.write_candidates(candidates)

    audit = AuditLogger(store.state_dir / AUDIT_FILENAME, args.run_id)
    audit.emit(
        "candidates_saved",
        message=f"Saved {len(candidates.candidates)} candidates",
        phase="phase-3-filtering",
        payload={
            "candidate_count": len(candidates.candidates),
            "honourable_count": len(candidates.honourable_mentions),
            "sources_scanned": candidates.sources_scanned,
        },
    )

    return {
        "run_id": args.run_id,
        "saved_path": str(saved_path),
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
