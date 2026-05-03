"""Entry point for `python -m tech_scout`.

Provides a thin command dispatcher that delegates to the per-task scripts in
`scripts/`. This module exists so users can run helpers without remembering
exact script paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

USAGE = """\
tech-scout — Claude Code-native plugin helpers.

Usage:
    python -m tech_scout <command> [args...]

Commands:
    doctor              Check environment and dependencies
    scan-codebase       Scan a codebase for tech stack profile
    list-history        List past research runs
    setup-run           Create a new run directory
    save-candidates     Save Phase 3 candidates to state
    load-candidates     Load saved candidates for resume
    render-doc          Render a Jinja2 template to markdown
    validate-package    Validate a generated research package
    locale-info         Inspect a locale or list all registered locales
    audit-show          Show the audit log for a research run

For detailed help on a command:
    python -m tech_scout <command> --help

Each command is also available as a standalone script:
    python scripts/ts_<command>.py
"""

_COMMAND_TO_SCRIPT: dict[str, str] = {
    "doctor": "ts_doctor.py",
    "scan-codebase": "ts_scan_codebase.py",
    "list-history": "ts_list_history.py",
    "setup-run": "ts_setup_run.py",
    "save-candidates": "ts_save_candidates.py",
    "load-candidates": "ts_load_candidates.py",
    "render-doc": "ts_render_doc.py",
    "validate-package": "ts_validate_package.py",
    "locale-info": "ts_locale_info.py",
    "audit-show": "ts_audit_show.py",
}


def main(argv: list[str] | None = None) -> int:
    """Dispatch a sub-command to its script.

    Returns the exit code from the dispatched script.
    """
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in {"-h", "--help", "help"}:
        sys.stdout.write(USAGE)
        return 0

    command = args[0]
    if command not in _COMMAND_TO_SCRIPT:
        sys.stderr.write(f"Unknown command: {command}\n\n{USAGE}")
        return 2

    script_name = _COMMAND_TO_SCRIPT[command]
    repo_root = Path(__file__).resolve().parent.parent.parent
    script_path = repo_root / "scripts" / script_name
    if not script_path.is_file():
        sys.stderr.write(
            f"Script not found: {script_path}\n"
            "Are you running from a source checkout? Helpers live in scripts/.\n"
        )
        return 2

    import runpy

    sys.argv = [str(script_path), *args[1:]]
    runpy.run_path(str(script_path), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
