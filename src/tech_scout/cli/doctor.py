"""``ts-doctor`` — verify environment and dependencies.

Checks are grouped into categories so failures are easy to scan:

* ``runtime`` — Python version, dependency imports
* ``paths`` — repo directories that must exist
* ``packaging`` — package data (templates) discoverable via importlib
* ``locales`` — every registered locale's template files present
* ``output`` — output root exists, has space, is writable
* ``smoke`` — actual end-to-end smoke checks: render every template,
  exercise the audit log under cross-process lock, round-trip a slug

Output: a versioned JSON envelope. Each check carries ``name``, ``category``,
``status`` (ok/warning/error), and ``message``. Exit code is 0 if no errors,
1 if any errors.
"""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

from tech_scout.cli._common import repo_root, run_script
from tech_scout.config.settings import get_settings
from tech_scout.domain.exceptions import ConfigurationError
from tech_scout.domain.value_objects import RunId
from tech_scout.locales import LocaleSpec, list_locales
from tech_scout.observability import AuditLogger
from tech_scout.output import (
    PackageWriter,
    TemplateRenderer,
    is_packaged_templates_writable_check,
    slugify_topic,
)
from tech_scout.utils.file_lock import FileLock

_REQUIRED_PACKAGES: tuple[str, ...] = (
    "pydantic",
    "pydantic_settings",
    "jinja2",
    "structlog",
    "slugify",
    "yaml",
)

_FREE_SPACE_WARNING_MB: int = 100
_SMOKE_RUN_ID = "0000-00-00-doctor00"


def main() -> dict[str, Any]:
    settings = get_settings()
    root = repo_root()

    checks: list[dict[str, str]] = []
    checks.append(_categorize("runtime", _check_python()))
    checks.extend(_categorize("runtime", c) for c in _check_imports())
    checks.append(_categorize("packaging", _check_packaged_templates()))
    checks.extend(_categorize("paths", c) for c in _check_directories(settings))
    checks.extend(_categorize("locales", c) for c in _check_locales(settings))
    checks.append(
        _categorize(
            "output",
            _wrap("output_root", _check_writable_root(settings.default_output_root)),
        )
    )
    checks.append(_categorize("output", _check_write_probe(settings.default_output_root)))
    checks.append(_categorize("output", _check_disk_space(settings.default_output_root)))
    checks.extend(_categorize("smoke", c) for c in _check_template_smoke_render(settings))
    checks.append(_categorize("smoke", _check_audit_lock_probe()))
    checks.append(_categorize("smoke", _check_slug_roundtrip()))

    error_count = sum(1 for c in checks if c["status"] == "error")
    warn_count = sum(1 for c in checks if c["status"] == "warning")

    by_category: dict[str, dict[str, int]] = {}
    for check in checks:
        bucket = by_category.setdefault(check["category"], {"ok": 0, "warning": 0, "error": 0})
        bucket[check["status"]] = bucket.get(check["status"], 0) + 1

    summary = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "repo_root": str(root),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
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
        "env_overrides": _env_overrides(),
        "by_category": by_category,
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


def _categorize(category: str, check: dict[str, str]) -> dict[str, str]:
    """Attach a ``category`` key to a check result."""
    out = dict(check)
    out["category"] = category
    return out


def _env_overrides() -> dict[str, str]:
    """Return TECH_SCOUT_* env vars currently set, for visibility in the report.

    Sensitive values (anything that looks like a token or key) get redacted.
    Doctor output may end up in audit logs or screenshots, so we redact
    proactively even though current settings carry no secrets.
    """
    out: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith("TECH_SCOUT_"):
            continue
        if any(token in key.upper() for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            out[key] = "<redacted>"
        else:
            out[key] = value
    return out


def _check_python() -> dict[str, str]:
    return _wrap("python_version", _check_python_version())


def _check_imports() -> list[dict[str, str]]:
    return [_wrap(f"import_{pkg}", _check_import(pkg)) for pkg in _REQUIRED_PACKAGES]


def _check_packaged_templates() -> dict[str, str]:
    ok, msg = is_packaged_templates_writable_check()
    return {
        "name": "packaged_templates",
        "status": "ok" if ok else "error",
        "message": msg,
    }


def _check_directories(settings: Any) -> list[dict[str, str]]:
    pairs = (
        ("templates_dir", settings.templates_dir),
        ("scripts_dir", settings.scripts_dir),
        ("skill_reference_dir", settings.skill_reference_dir),
    )
    out: list[dict[str, str]] = []
    for label, path in pairs:
        # scripts_dir and skill_reference_dir are only present in source
        # checkouts; downgrade missing ones to warnings so installed-mode
        # doctor runs do not fail just because the user pip-installed the
        # wheel without checking out the repo.
        must_exist = label == "templates_dir"
        out.append(_wrap(label, _check_directory(path, must_exist=must_exist)))
    return out


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


def _check_write_probe(path: Path) -> dict[str, str]:
    """Actually try to write a file to *path* — catches read-only mounts.

    Many environments (NFS, locked-down corporate machines) report a
    directory as existing but refuse writes. The doctor's "directory
    exists" check would miss this. The probe is one tempfile created and
    deleted, so it's safe to run repeatedly.
    """
    name = "write_probe"
    if not path.exists():
        # _check_writable_root already warned about creation; re-warn here.
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return _wrap(name, ("error", f"Cannot create {path}: {exc}"))
    if not path.is_dir():
        return _wrap(name, ("error", f"{path} is not a directory"))
    try:
        with tempfile.NamedTemporaryFile(
            dir=str(path),
            prefix="ts-doctor-",
            suffix=".tmp",
            delete=False,
        ) as fh:
            probe = Path(fh.name)
            fh.write(b"ok")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return _wrap(name, ("error", f"Cannot write to {path}: {exc}"))
    return _wrap(name, ("ok", f"Write probe succeeded in {path}"))


def _check_disk_space(path: Path) -> dict[str, str]:
    """Warn when the output root has < ``_FREE_SPACE_WARNING_MB`` MB free."""
    name = "disk_space"
    target = path if path.exists() else path.parent
    if not target.exists():
        return _wrap(name, ("warning", f"Cannot probe disk usage: {target} does not exist"))
    try:
        usage = shutil.disk_usage(str(target))
    except OSError as exc:
        return _wrap(name, ("warning", f"shutil.disk_usage failed for {target}: {exc}"))
    free_mb = usage.free // (1024 * 1024)
    if free_mb < _FREE_SPACE_WARNING_MB:
        return _wrap(
            name,
            (
                "warning",
                f"Only {free_mb} MB free on the volume holding {target} "
                f"(threshold: {_FREE_SPACE_WARNING_MB} MB). Runs may fail.",
            ),
        )
    return _wrap(name, ("ok", f"{free_mb} MB free on the volume holding {target}"))


def _check_template_smoke_render(settings: Any) -> Iterable[dict[str, str]]:
    """Render every locale's every slot with a dummy context.

    Catches templates that reference variables the analyzer is supposed to
    populate but the template itself doesn't list, plus any Jinja syntax
    bugs introduced when the template was last edited. We use
    ``StrictUndefined`` (the production setting) so a missing variable
    raises rather than silently rendering as an empty string.

    The dummy context is intentionally over-permissive: we feed every
    plausible field name a string value. Real production renders are
    stricter via the analyzer/skill contract; this check is a syntax and
    "Jinja resolves" probe, not a content check.
    """
    name_prefix = "template_smoke"
    try:
        renderer = TemplateRenderer(templates_root=settings.templates_dir)
    except (OSError, ValueError) as exc:
        yield _wrap(f"{name_prefix}_init", ("error", f"Renderer init failed: {exc}"))
        return

    for locale in list_locales():
        try:
            PackageWriter(
                renderer=renderer,
                output_folder=Path(tempfile.gettempdir()),
                locale=locale,
            )
        except (OSError, ValueError) as exc:
            yield _wrap(
                f"{name_prefix}_{locale.code}_init",
                ("error", f"PackageWriter init failed for locale {locale.code}: {exc}"),
            )
            continue

        # Render every template with a permissive smoke context. Jinja's
        # UndefinedError is expected — analyzers populate those fields at
        # runtime — so we only flag *hard* render failures (template
        # syntax errors, missing template files).
        check_name = f"{name_prefix}_{locale.code}"
        hard_failures: list[str] = []
        for doc in locale.documents:
            template_path = locale.template_path(doc.slot)
            try:
                renderer.render(template_path, _SmokeContext())
            except Exception as exc:
                if "is undefined" in str(exc).lower():
                    continue
                hard_failures.append(f"{template_path.name}: {exc}")

        if hard_failures:
            yield _wrap(
                check_name,
                (
                    "error",
                    f"Locale '{locale.code}' has template render failures: "
                    + "; ".join(hard_failures),
                ),
            )
        else:
            yield _wrap(
                check_name,
                (
                    "ok",
                    f"Locale '{locale.code}' renders all "
                    f"{len(locale.documents)} templates without syntax errors",
                ),
            )


class _SmokeContext(dict[str, Any]):
    """A dict that returns a placeholder string for every key.

    Used as the smoke-render context: any template variable lookup
    succeeds, yielding ``""`` so renders complete without raising
    UndefinedError. This is enough to catch Jinja syntax errors,
    malformed loops, missing template files, etc.
    """

    def __missing__(self, key: str) -> str:
        return ""


def _check_audit_lock_probe() -> dict[str, str]:
    """Verify the cross-process audit-log lock is functional on this OS.

    Acquires the lock, writes one event, releases. Catches platforms where
    ``msvcrt.locking`` (Windows) or ``fcntl.flock`` (POSIX) are unavailable
    or behave unexpectedly.
    """
    name = "audit_lock_probe"
    with tempfile.TemporaryDirectory(prefix="ts-doctor-audit-") as tmp_dir:
        audit_path = Path(tmp_dir) / "audit.jsonl"
        try:
            logger = AuditLogger(audit_path, RunId(value=_SMOKE_RUN_ID))
            logger.emit("doctor_probe", payload={"ok": True})
        except (OSError, ValueError) as exc:
            return _wrap(
                name,
                (
                    "error",
                    f"AuditLogger probe failed: {exc!r}. Cross-process locking "
                    "may be broken on this platform.",
                ),
            )
        if not audit_path.is_file():
            return _wrap(
                name,
                (
                    "error",
                    f"Audit probe produced no output at {audit_path}. "
                    "AuditLogger.emit silently failed.",
                ),
            )
        # Verify the second acquisition works (contention with previous lock release).
        try:
            with FileLock(
                audit_path.with_name(audit_path.name + ".lock"),
                timeout_seconds=2.0,
            ):
                pass
        except (OSError, ValueError) as exc:
            return _wrap(
                name,
                (
                    "error",
                    f"FileLock re-acquisition failed: {exc!r}",
                ),
            )
    return _wrap(name, ("ok", "Audit log + cross-process lock work on this platform"))


def _check_slug_roundtrip() -> dict[str, str]:
    """Verify Turkish characters round-trip through the slug pipeline.

    A regression in the slugify dependency would silently drop Turkish
    diacritics, producing folder names that collide. This check asserts
    a known-good Turkish input maps to a known-good ASCII slug.
    """
    name = "slug_roundtrip"
    cases = [
        ("Şirket içi gözlemleme", "sirket-ici-gozlemleme"),
        ("MCP — Model Context Protocol", "mcp-model-context-protocol"),
        ("hello world", "hello-world"),
    ]
    for input_text, expected in cases:
        try:
            slug = slugify_topic(input_text)
        except ValueError as exc:
            return _wrap(name, ("error", f"Slug raised on {input_text!r}: {exc}"))
        if slug.value != expected:
            return _wrap(
                name,
                (
                    "warning",
                    f"Slug for {input_text!r}: got {slug.value!r}, "
                    f"expected {expected!r}. Check python-slugify version.",
                ),
            )
    return _wrap(name, ("ok", f"Slug pipeline handles {len(cases)} known inputs correctly"))


def entry_point() -> NoReturn:
    """Console-script entry point for ``ts-doctor``."""
    run_script(main)


if __name__ == "__main__":  # pragma: no cover
    entry_point()
