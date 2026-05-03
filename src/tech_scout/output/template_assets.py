"""Locate the bundled Jinja2 template directory regardless of install mode.

Templates are shipped as package data under ``src/tech_scout/templates/``.
That layout means they are present whether the package was installed via
``pip install`` (where they live inside ``site-packages``) or run from a
source checkout (where they live in the repository tree).

The lookup is deliberately tolerant: if the package's resources are not
on a real filesystem (e.g., the wheel is loaded as a zip), we fall back
to extracting the templates into a temporary directory the first time and
caching the path. In the common case (wheel unpacked into site-packages,
or running from source) the resources are already on disk and the call
returns instantly.
"""

from __future__ import annotations

import atexit
import shutil
import tempfile
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from tech_scout.domain.exceptions import ConfigurationError

if TYPE_CHECKING:
    # importlib.resources.abc.Traversable lacks runtime type stubs on some
    # Python versions; we only need it for annotations.
    from importlib.abc import Traversable

_PACKAGE: str = "tech_scout"
_RESOURCE: str = "templates"


@lru_cache(maxsize=1)
def packaged_templates_root() -> Path:
    """Return the on-disk path to the bundled templates directory.

    Raises :class:`ConfigurationError` if the bundle cannot be located —
    this should be impossible after a successful install but surfaces a
    clear error if the wheel was tampered with.
    """
    try:
        traversable: Traversable = resources.files(_PACKAGE).joinpath(_RESOURCE)
    except (ModuleNotFoundError, FileNotFoundError) as exc:
        msg = f"Cannot locate bundled templates for package {_PACKAGE!r}"
        raise ConfigurationError(msg, context={"package": _PACKAGE}) from exc

    # Common case: the resource is already on a real filesystem (regular
    # site-packages install or a source checkout). importlib.resources
    # exposes this via the ``as_file`` context manager, but for static
    # paths we can short-circuit.
    direct = _maybe_direct_path(traversable)
    if direct is not None and direct.is_dir():
        return direct

    # Fallback: extract into a temp dir for the lifetime of the process.
    return _materialize_to_temp(traversable)


def is_packaged_templates_writable_check() -> tuple[bool, str]:
    """Return ``(ok, message)`` describing the templates' on-disk state.

    Used by ``ts_doctor`` to verify the install is intact. The check
    succeeds when the directory exists, contains the expected locale
    subdirectories, and at least one ``.md.j2`` file lives in each.
    """
    try:
        root = packaged_templates_root()
    except ConfigurationError as exc:
        return False, str(exc)
    if not root.is_dir():
        return False, f"Templates root is not a directory: {root}"
    locales_found = sorted(p.name for p in root.iterdir() if p.is_dir())
    if not locales_found:
        return False, f"Templates root has no locale subdirectories: {root}"
    for locale_dir in (root / name for name in locales_found):
        if not any(p.suffix == ".j2" for p in locale_dir.iterdir() if p.is_file()):
            return False, f"Locale subdir {locale_dir} contains no .j2 templates"
    return True, f"Templates available at {root} ({', '.join(locales_found)})"


def _maybe_direct_path(traversable: Traversable) -> Path | None:
    """Return a :class:`Path` for *traversable* if it is already on disk."""
    candidate = getattr(traversable, "_path", None) or getattr(traversable, "name", None)
    if isinstance(traversable, Path):
        return traversable
    if isinstance(candidate, (str, Path)):
        try:
            path = Path(str(candidate))
        except (TypeError, ValueError):
            return None
        if path.is_absolute() and path.exists():
            return path
    # A common attribute on PosixPath-like Traversable instances:
    str_form = str(traversable)
    path = Path(str_form)
    if path.is_absolute() and path.exists():
        return path
    return None


def _materialize_to_temp(traversable: Traversable) -> Path:
    """Copy *traversable* into a tempdir and return the new on-disk root.

    Registered for cleanup on process exit so we do not leak directories
    across long-running test sessions.
    """
    tmp = Path(tempfile.mkdtemp(prefix="tech-scout-templates-"))
    atexit.register(_safe_cleanup, tmp)
    _copy_traversable(traversable, tmp)
    return tmp


def _copy_traversable(src: Traversable, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        target = dst / entry.name
        if entry.is_dir():
            _copy_traversable(entry, target)
        elif entry.is_file():
            with entry.open("rb") as fh:
                target.write_bytes(fh.read())


def _safe_cleanup(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


__all__ = [
    "is_packaged_templates_writable_check",
    "packaged_templates_root",
]
