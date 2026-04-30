"""tech-scout locale-info — emit a LocaleSpec as JSON.

Usage::

    python scripts/ts_locale_info.py --code en
    python scripts/ts_locale_info.py --code turkish
    python scripts/ts_locale_info.py --list

The skill calls this once per run (after ``ts_setup_run.py``) so it can
render the Stage-A selection prompt, candidate-display labels, and final
summary in the user-selected language without hardcoding any locale text
in markdown.

Output: JSON envelope with the full :class:`LocaleSpec` (when ``--code`` is
given) or a list of registered locales (when ``--list`` is given).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import emit_error, emit_success
from tech_scout.locales import (
    DEFAULT_LOCALE_CODE,
    LocaleSpec,
    get_locale,
    list_locales,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts_locale_info",
        description="Look up a registered locale or list all registered locales.",
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--code",
        help=(
            "Locale code or alias (e.g. 'en', 'tr', 'english', 'turkish'). "
            f"Defaults to '{DEFAULT_LOCALE_CODE}' if --list is not used."
        ),
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="List every registered locale (code, display name, aliases).",
    )
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()

    if args.list:
        return {
            "locales": [_brief(spec) for spec in list_locales()],
            "default_code": DEFAULT_LOCALE_CODE,
        }

    code = args.code or DEFAULT_LOCALE_CODE
    spec = get_locale(code)
    return {
        "default_code": DEFAULT_LOCALE_CODE,
        "spec": _full(spec),
    }


def _brief(spec: LocaleSpec) -> dict[str, Any]:
    return {
        "code": spec.code,
        "display_name": spec.display_name,
        "aliases": list(spec.aliases),
        "language": spec.language.value,
        "template_subdir": spec.template_subdir,
        "filenames": [d.filename for d in spec.documents],
    }


def _full(spec: LocaleSpec) -> dict[str, Any]:
    return {
        "code": spec.code,
        "display_name": spec.display_name,
        "aliases": list(spec.aliases),
        "language": spec.language.value,
        "template_subdir": spec.template_subdir,
        "documents": [
            {
                "slot": d.slot.value,
                "filename": d.filename,
                "template_filename": d.template_filename,
                "min_words": d.min_words,
                "required_section_keywords": list(d.required_section_keywords),
            }
            for d in spec.documents
        ],
        "selection_prompt": spec.selection_prompt,
        "selection_examples": list(spec.selection_examples),
        "final_summary_template": spec.final_summary_template,
        "candidate_display_labels": dict(spec.candidate_display_labels),
        "score_axis_labels": dict(spec.score_axis_labels),
        "fit_label_map": dict(spec.fit_label_map),
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
