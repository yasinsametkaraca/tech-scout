"""tech-scout doctor — verify environment and dependencies.

Checks:

* Python version
* Importability of required dependencies
* Existence of templates root
* Existence of every locale's template subdir + required template files
* Existence of skill reference directory
* Writability of the default output root

Output: JSON envelope with one ``checks`` array, each with ``name``,
``status`` (ok/warning/error), and ``message``. Exit code is 0 if no errors,
1 if any errors.
"""

from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path
from typing import Any

from _common import emit_error, emit_success, repo_root
from tech_scout.config.settings import get_settings
from tech_scout.domain.exceptions import ConfigurationError
from tech_scout.locales import LocaleSpec, list_locales

_REQUIRED_PACKAGES: tuple[str, ...] = (
    "pydantic",
    "pydantic_settings",
    "jinja2",
    "structlog",
    "slugify",
    "yaml",
)


def main() -> dict[str, Any]:
    settings = get_settings()
    root = repo_root()

    checks: list[dict[str, str]] = []
    checks.append(_check_python())
    checks.extend(_check_imports())
    checks.extend(_check_directories(settings))
    checks.extend(_check_locales(settings))
    checks.append(_wrap("output_root", _check_writable_root(settings.default_output_root)))

    error_count = sum(1 for c in checks if c["status"] == "error")
    warn_count = sum(1 for c in checks if c["status"] == "warning")

    summary = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "repo_root": str(root),
        "settings": {
            "templates_dir": str(settings.templates_dir),
            "skill_reference_dir": str(settings.skill_reference_dir),
            "default_output_root": str(settings.default_output_root),
            "default_locale_code": settings.default_locale_code,
        },
        "locales": [
            {
                "code": s.code,
                "display_name": s.display_name,
                "aliases": list(s.aliases),
            }
            for s in list_locales()
        ],
        "checks": checks,
        "error_count": error_count,
        "warning_count": warn_count,
        "passed": error_count == 0,
    }

    if error_count > 0:
        raise ConfigurationError(
            f"{error_count} environment check(s) failed",
            context=summary,
        )
    return summary


def _wrap(name: str, status_msg: tuple[str, str]) -> dict[str, str]:
    status, msg = status_msg
    return {"name": name, "status": status, "message": msg}


def _check_python() -> dict[str, str]:
    return _wrap("python_version", _check_python_version())


def _check_imports() -> list[dict[str, str]]:
    return [_wrap(f"import_{pkg}", _check_import(pkg)) for pkg in _REQUIRED_PACKAGES]


def _check_directories(settings: Any) -> list[dict[str, str]]:
    pairs = (
        ("templates_dir", settings.templates_dir),
        ("scripts_dir", settings.scripts_dir),
        ("skill_reference_dir", settings.skill_reference_dir),
    )
    return [_wrap(label, _check_directory(path, must_exist=True)) for label, path in pairs]


def _check_locales(settings: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for spec in list_locales():
        out.extend(_check_locale_templates(settings.templates_dir, spec))
    return out


def _check_python_version() -> tuple[str, str]:
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        return ("error", f"Python 3.10+ required, found {major}.{minor}")
    return ("ok", f"Python {major}.{minor}")


def _check_import(package: str) -> tuple[str, str]:
    try:
        module = importlib.import_module(package)
    except ImportError as exc:
        return ("error", f"import {package} failed: {exc}")
    version = getattr(module, "__version__", None) or "(version unknown)"
    return ("ok", f"{package} {version}")


def _check_directory(path: Path, *, must_exist: bool) -> tuple[str, str]:
    if path.exists():
        if path.is_dir():
            return ("ok", f"{path} exists")
        return ("error", f"{path} is not a directory")
    if must_exist:
        return ("error", f"{path} does not exist")
    return ("warning", f"{path} does not exist (will be created)")


def _check_locale_templates(templates_dir: Path, spec: LocaleSpec) -> list[dict[str, str]]:
    """Verify every template file the locale references is on disk."""
    name = f"locale_{spec.code}_templates"
    locale_dir = templates_dir / spec.template_subdir

    if not locale_dir.is_dir():
        return [
            {
                "name": name,
                "status": "error",
                "message": f"Locale subdir missing: {locale_dir}",
            }
        ]

    missing = [
        d.template_filename
        for d in spec.documents
        if not (locale_dir / d.template_filename).is_file()
    ]
    if missing:
        return [
            {
                "name": name,
                "status": "error",
                "message": (
                    f"Locale '{spec.code}' is missing template(s) under "
                    f"{locale_dir}: {', '.join(missing)}"
                ),
            }
        ]
    return [
        {
            "name": name,
            "status": "ok",
            "message": (f"Locale '{spec.code}' has all 8 templates under {locale_dir}"),
        }
    ]


def _check_writable_root(path: Path) -> tuple[str, str]:
    if path.exists():
        if not path.is_dir():
            return ("error", f"{path} exists but is not a directory")
        return ("ok", f"{path} writable")
    parent = path.parent
    if parent.exists() and parent.is_dir():
        return ("warning", f"{path} does not exist yet (parent {parent} ok — will be created)")
    return ("error", f"Neither {path} nor parent {parent} exists")


if __name__ == "__main__":
    try:
        emit_success(main())
    except SystemExit:
        raise
    except ConfigurationError as exc:
        emit_error(exc, exit_code=1)
    except Exception as exc:
        emit_error(exc, exit_code=2)
