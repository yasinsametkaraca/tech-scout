"""Path-safety utilities.

These helpers prevent directory-traversal mistakes and normalize path
representations consistently across Windows and POSIX.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath


def normalize_path(path: Path | str) -> Path:
    """Return an absolute, resolved Path with separators normalized.

    Resolves symlinks and ``..`` segments. Does not require the path to
    exist; intermediate non-existent parts are kept literally.
    """
    p = Path(path) if isinstance(path, str) else path
    return p.expanduser().resolve()


def is_within_directory(child: Path | str, parent: Path | str) -> bool:
    """Return True if *child* is inside *parent* (after resolution).

    Used to enforce that file writes stay within an output folder, and that
    user-supplied paths cannot escape via ``..`` traversal.
    """
    try:
        child_resolved = normalize_path(child)
        parent_resolved = normalize_path(parent)
    except (OSError, RuntimeError):
        return False

    try:
        child_resolved.relative_to(parent_resolved)
    except ValueError:
        return False
    return True


def safe_relative_path(child: Path | str, parent: Path | str) -> PurePosixPath:
    """Return *child* relative to *parent*, raising if traversal is detected.

    Raises :class:`ValueError` if *child* is not inside *parent*. The result
    is a :class:`PurePosixPath` so ``str()`` always uses ``/`` separators on
    every platform — useful for log messages and JSON serialization.
    """
    if not is_within_directory(child, parent):
        msg = f"Path {child!r} is not within {parent!r}"
        raise ValueError(msg)
    rel = normalize_path(child).relative_to(normalize_path(parent))
    return PurePosixPath(rel.as_posix())


def ensure_directory(path: Path | str, *, mode: int = 0o755) -> Path:
    """Create *path* as a directory (and parents) if needed; return resolved path.

    Idempotent: calling twice on the same path is fine. Raises :class:`OSError`
    if the path exists as a non-directory.
    """
    p = Path(path)
    if p.exists() and not p.is_dir():
        msg = f"Path exists but is not a directory: {p}"
        raise OSError(msg)
    p.mkdir(parents=True, exist_ok=True, mode=mode)
    return normalize_path(p)


def windows_to_posix(path: Path | str) -> str:
    """Convert a Windows-style path to a POSIX-style string.

    ``C:\\foo\\bar`` -> ``/c/foo/bar`` (matches Git Bash / MSYS). On non-Windows,
    returns the string form unchanged.
    """
    s = str(path)
    if os.name != "nt":
        return s.replace("\\", "/")
    drive, rest = os.path.splitdrive(s)
    if drive:
        letter = drive[0].lower()
        rest_posix = rest.replace("\\", "/")
        return f"/{letter}{rest_posix}"
    return s.replace("\\", "/")
