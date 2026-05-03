"""``ts-setup-run`` — create the output folder and initial run state."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

from tech_scout.cli._common import parse_path, run_script
from tech_scout.domain.enums import (
    Depth,
    Phase,
    PhaseStatus,
)
from tech_scout.domain.models import (
    PhaseProgress,
    ResearchRequest,
    RunSnapshot,
)
from tech_scout.locales import get_locale, get_locale_for_language
from tech_scout.observability import AuditLogger, bind_run_id
from tech_scout.output.slug import build_run_id
from tech_scout.state import AUDIT_FILENAME, STATE_FILENAME, StateStore
from tech_scout.utils.path_safety import ensure_directory

_LANGUAGE_CHOICES = ("en", "tr", "english", "turkish")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts-setup-run",
        description="Create the output folder and initial run state for a research run.",
    )
    p.add_argument("--output-folder", type=parse_path, required=True)
    p.add_argument("--company-name", default=None)
    p.add_argument("--company-description", default=None)
    p.add_argument(
        "--company-website",
        default=None,
        help=(
            "Company website URL. Phase 1 will WebFetch it for domain "
            "context when no --codebase-path is provided."
        ),
    )
    p.add_argument("--codebase-path", type=parse_path, default=None)
    p.add_argument("--focus-area", default=None)
    p.add_argument(
        "--depth",
        choices=[d.value for d in Depth],
        default=Depth.STANDARD.value,
    )
    p.add_argument(
        "--language",
        choices=_LANGUAGE_CHOICES,
        default="en",
        help="Output language for the package (en/tr or english/turkish).",
    )
    p.add_argument(
        "--slack-language",
        choices=_LANGUAGE_CHOICES,
        default=None,
        help="Override the language of the slack-summary doc only. Defaults to --language.",
    )
    p.add_argument("--prior-research-root", type=parse_path, default=None)
    p.add_argument(
        "--force",
        action="store_true",
        help="Always create a fresh run-id even if one already exists in the output folder",
    )
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()

    output_folder = ensure_directory(args.output_folder)

    package_locale = get_locale(args.language)
    slack_locale = (
        get_locale(args.slack_language) if args.slack_language is not None else package_locale
    )

    existing_run_id = _find_existing_run_id(output_folder)
    if existing_run_id and not args.force:
        store = StateStore(output_folder, existing_run_id)
        snapshot = store.read_run_snapshot()
        if snapshot is not None:
            bind_run_id(str(snapshot.run_id))
            existing_locale = get_locale_for_language(snapshot.request.language)
            existing_slack_locale = get_locale_for_language(snapshot.request.slack_language)
            return {
                "run_id": str(snapshot.run_id),
                "state_dir": str(store.state_dir),
                "output_folder": str(output_folder),
                "language": snapshot.request.language.value,
                "slack_language": snapshot.request.slack_language.value,
                "locale_code": existing_locale.code,
                "slack_locale_code": existing_slack_locale.code,
                "reused": True,
            }

    request = ResearchRequest(
        company_name=args.company_name,
        company_description=args.company_description,
        company_website=args.company_website,
        codebase_path=args.codebase_path,
        focus_area=args.focus_area,
        output_folder=output_folder,
        language=package_locale.language,
        slack_language=slack_locale.language,
        depth=Depth(args.depth),
        prior_research_root=args.prior_research_root,
    )

    run_id = build_run_id()
    bind_run_id(str(run_id))

    store = StateStore(output_folder, run_id)
    store.initialize()

    now = datetime.now()
    snapshot = RunSnapshot(
        run_id=run_id,
        request=request,
        phases=tuple(_initial_phases()),
        current_phase=Phase.PREPARATION,
        started_at=now,
        last_updated=now,
    )

    store.write_run_snapshot(snapshot)

    audit = AuditLogger(store.state_dir / AUDIT_FILENAME, run_id)
    audit.emit(
        "run_initialized",
        message="Research run created and state initialized",
        phase=Phase.PREPARATION.value,
        payload={
            "depth": request.depth.value,
            "language": request.language.value,
            "slack_language": request.slack_language.value,
            "locale_code": package_locale.code,
            "slack_locale_code": slack_locale.code,
            "has_codebase": request.has_codebase,
            "has_company_context": request.has_company_context,
        },
    )

    return {
        "run_id": str(run_id),
        "state_dir": str(store.state_dir),
        "state_file": str(store.state_dir / STATE_FILENAME),
        "audit_file": str(store.state_dir / AUDIT_FILENAME),
        "output_folder": str(output_folder),
        "language": request.language.value,
        "slack_language": request.slack_language.value,
        "locale_code": package_locale.code,
        "slack_locale_code": slack_locale.code,
        "reused": False,
    }


def _initial_phases() -> list[PhaseProgress]:
    return [PhaseProgress(phase=p, status=PhaseStatus.NOT_STARTED) for p in Phase]


def _find_existing_run_id(output_folder: Path) -> str | None:
    state_root = output_folder / ".tech-scout"
    if not state_root.is_dir():
        return None
    candidates = [d for d in state_root.iterdir() if d.is_dir()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.name


def entry_point() -> NoReturn:
    if "--help" in sys.argv or "-h" in sys.argv:
        _build_parser().print_help()
        raise SystemExit(0)
    run_script(main)


if __name__ == "__main__":  # pragma: no cover
    entry_point()
