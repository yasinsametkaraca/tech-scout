"""tech-scout render-doc — render a single Jinja2 template to a markdown file.

Usage::

    python scripts/ts_render_doc.py
        --slot {executive_summary|detailed_analysis|presentation|
                quick_reference|diagrams|slack_summary|sources|readme}
        --context-file PATH
        --output-folder PATH
        [--locale-code en|tr|english|turkish]
        [--slack-locale-code en|tr|english|turkish]
        [--run-id RUN_ID]
        [--templates-root PATH]

The skill produces the analysis content in JSON, hands it to this script,
and the script renders the template that the active locale maps to. Phase
5 calls this script once per slot.

Output: JSON envelope with the slot, locale code, and the written file path.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _common import emit_error, emit_success, parse_path, repo_root
from tech_scout.config.settings import get_settings
from tech_scout.domain.enums import OutputDocSlot
from tech_scout.domain.exceptions import TemplateRenderError
from tech_scout.locales import DEFAULT_LOCALE_CODE, get_locale
from tech_scout.observability import AuditLogger, bind_run_id
from tech_scout.output import PackageWriter, TemplateRenderer
from tech_scout.state import AUDIT_FILENAME, StateStore


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts_render_doc",
        description="Render a single document of the research package.",
    )
    p.add_argument(
        "--slot",
        required=True,
        choices=[s.value for s in OutputDocSlot],
        help="Which slot to render (language-neutral identifier)",
    )
    p.add_argument(
        "--context-file",
        type=parse_path,
        required=True,
        help="JSON file containing the template context dict",
    )
    p.add_argument("--output-folder", type=parse_path, required=True)
    p.add_argument(
        "--locale-code",
        default=DEFAULT_LOCALE_CODE,
        help="Locale code or alias (e.g. 'en', 'tr'). Defaults to settings.",
    )
    p.add_argument(
        "--slack-locale-code",
        default=None,
        help=("Override the locale for the slack-summary slot only. Defaults to --locale-code."),
    )
    p.add_argument(
        "--run-id",
        default=None,
        help="Optional run id (for audit log emission)",
    )
    p.add_argument(
        "--templates-root",
        type=parse_path,
        default=None,
        help="Override templates root (defaults to settings.templates_dir)",
    )
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()

    if not args.context_file.is_file():
        raise TemplateRenderError(
            f"Context file does not exist: {args.context_file}",
            context={"path": str(args.context_file)},
        )

    raw = args.context_file.read_text(encoding="utf-8")
    try:
        context = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TemplateRenderError(
            f"Context file is not valid JSON: {args.context_file}",
            context={"path": str(args.context_file), "error": str(exc)},
        ) from exc

    if not isinstance(context, dict):
        raise TemplateRenderError(
            "Context file must be a JSON object",
            context={"path": str(args.context_file)},
        )

    settings = get_settings()
    templates_root = args.templates_root or settings.templates_dir
    if not templates_root.is_dir():
        # Fall back to repo-root/templates (handy when running from source)
        fallback = repo_root() / "templates"
        if fallback.is_dir():
            templates_root = fallback
        else:
            raise TemplateRenderError(
                f"Templates root does not exist: {templates_root}",
                context={"templates_root": str(templates_root)},
            )

    package_locale = get_locale(args.locale_code)
    slack_locale = (
        get_locale(args.slack_locale_code) if args.slack_locale_code is not None else package_locale
    )

    args.output_folder.mkdir(parents=True, exist_ok=True)

    renderer = TemplateRenderer(templates_root=templates_root)
    writer = PackageWriter(
        renderer=renderer,
        output_folder=args.output_folder,
        locale=package_locale,
        slack_locale=slack_locale,
    )
    slot = OutputDocSlot(args.slot)
    written = writer.write_doc(slot, context)
    active_locale = slack_locale if slot == OutputDocSlot.SLACK_SUMMARY else package_locale

    if args.run_id:
        bind_run_id(args.run_id)
        store = StateStore(args.output_folder, args.run_id)
        if store.state_dir.exists():
            audit = AuditLogger(store.state_dir / AUDIT_FILENAME, args.run_id)
            audit.emit(
                "doc_rendered",
                message=f"Rendered {active_locale.filename_for(slot)}",
                phase="phase-5-packaging",
                payload={
                    "slot": slot.value,
                    "filename": active_locale.filename_for(slot),
                    "locale_code": active_locale.code,
                    "path": str(written),
                },
            )

    return {
        "slot": slot.value,
        "filename": active_locale.filename_for(slot),
        "locale_code": active_locale.code,
        "written_path": str(written),
        "templates_root": str(templates_root),
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
