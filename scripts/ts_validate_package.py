"""tech-scout validate-package — Phase 6 quality check.

Usage::

    python scripts/ts_validate_package.py
        --output-folder PATH
        [--locale-code en|tr|english|turkish]
        [--slack-locale-code en|tr|english|turkish]
        [--run-id RUN_ID]

Runs :class:`PackageValidator` against the active locale's expected
filenames + required-section keywords. Exit code is 0 if no errors
(warnings only), 1 if any error issues exist or required documents are
missing.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _common import emit_error, emit_success, parse_path
from tech_scout.domain.exceptions import ValidationError
from tech_scout.locales import DEFAULT_LOCALE_CODE, get_locale
from tech_scout.observability import AuditLogger, bind_run_id
from tech_scout.output import PackageValidator
from tech_scout.state import AUDIT_FILENAME, StateStore


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts_validate_package",
        description="Run Phase 6 quality validation on a research package.",
    )
    p.add_argument("--output-folder", type=parse_path, required=True)
    p.add_argument(
        "--locale-code",
        default=DEFAULT_LOCALE_CODE,
        help="Locale code or alias used to render this package.",
    )
    p.add_argument(
        "--slack-locale-code",
        default=None,
        help="Locale of the slack-summary slot (defaults to --locale-code).",
    )
    p.add_argument("--run-id", default=None)
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()

    package_locale = get_locale(args.locale_code)
    slack_locale = (
        get_locale(args.slack_locale_code) if args.slack_locale_code is not None else package_locale
    )

    validator = PackageValidator(locale=package_locale, slack_locale=slack_locale)
    report = validator.validate(args.output_folder)

    if args.run_id:
        bind_run_id(args.run_id)
        store = StateStore(args.output_folder, args.run_id)
        if store.state_dir.exists():
            audit = AuditLogger(store.state_dir / AUDIT_FILENAME, args.run_id)
            audit.emit(
                "package_validated",
                message=(
                    f"errors={report.error_count} warnings={report.warning_count} "
                    f"missing={len(report.documents_missing)}"
                ),
                phase="phase-6-quality-check",
                severity="info" if report.passed else "error",
                payload={
                    "passed": report.passed,
                    "error_count": report.error_count,
                    "warning_count": report.warning_count,
                    "missing": list(report.documents_missing),
                    "locale_code": package_locale.code,
                    "slack_locale_code": slack_locale.code,
                },
            )

    body: dict[str, Any] = {
        "package_path": str(report.package_path),
        "locale_code": package_locale.code,
        "slack_locale_code": slack_locale.code,
        "passed": report.passed,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "documents_present": list(report.documents_present),
        "documents_missing": list(report.documents_missing),
        "issues": [
            {
                "severity": i.severity,
                "document": i.document,
                "section": i.section,
                "message": i.message,
            }
            for i in report.issues
        ],
    }

    if not report.passed:
        raise ValidationError(
            f"Package failed validation: {report.error_count} errors, "
            f"{len(report.documents_missing)} missing documents",
            context=body,
        )

    return body


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
