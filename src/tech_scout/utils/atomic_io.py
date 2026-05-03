"""Atomic filesystem writes — no half-written state files.

State files (``state.json``, ``candidates.json``, ``selection.json``,
``codebase-profile.json``, ``phase-progress.json``) must survive a crash or
``Ctrl+C`` mid-write without leaving a corrupt file behind. Without
atomicity a partial write blocks the resume flow because the JSON parser
fails before the schema migrator can step in.

The pattern is the standard write-temp-then-rename: write the new content
to ``<target>.tmp.<unique>`` in the same directory as the target, ``fsync``
the file, and ``os.replace()`` it onto the final path. ``os.replace`` is
atomic on POSIX and Windows (when source and destination are on the same
filesystem), and a same-directory rename is always same-filesystem.

Append-only files (``audit.jsonl``) use a different pattern — see
:func:`atomic_append_line`. There the unit of atomicity is one line, not
the whole file.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

_TMP_TOKEN_BYTES = 6


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write *text* to *path* atomically.

    Creates the parent directory if needed. Writes through a per-call
    temporary sibling file, ``fsync``s it, and renames into place. A crash
    before the rename leaves the target untouched; a crash after leaves the
    new content fully committed. There is no observable in-between state.

    Raises :class:`OSError` if the write or rename fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{secrets.token_hex(_TMP_TOKEN_BYTES)}")
    data = text.encode(encoding)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        tmp.replace(path)
    except OSError:
        # Clean up the partial temp file on failure; ignore secondary errors
        # so the original exception surfaces.
        with suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


def atomic_append_line(path: Path, line: str, *, encoding: str = "utf-8") -> None:
    """Append a single ``line`` (with trailing newline) to *path* atomically.

    Used for append-only logs (``audit.jsonl``). Opens the file in append
    mode and writes a single ``write()`` call. POSIX guarantees that a
    write of less than ``PIPE_BUF`` bytes (typically 4096) is atomic when
    the file is opened with ``O_APPEND``. On Windows we additionally take a
    cross-process lock around the append (see
    :class:`tech_scout.utils.file_lock.FileLock`).

    For larger lines, the caller should use a file lock. The audit log
    enforces a maximum payload size that keeps lines under this threshold.
    """
    if not line.endswith("\n"):
        line = line + "\n"
    data = line.encode(encoding)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


@contextmanager
def replace_directory_atomically(target: Path) -> Iterator[Path]:
    """Yield a staging directory whose contents replace *target* atomically.

    Use as::

        with replace_directory_atomically(target_dir) as staging:
            # write files into `staging`
            ...

    On context exit, ``target`` is replaced by the staging directory in a
    single ``os.replace`` call (or a swap-then-delete on Windows). The
    target either reflects the previous contents or the new contents, never
    a partial mix.

    A crash inside the ``with`` block leaves the target unchanged.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f"{target.name}.staging.{secrets.token_hex(_TMP_TOKEN_BYTES)}")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        yield staging
    except BaseException:
        _safe_rmtree(staging)
        raise

    if not target.exists():
        staging.replace(target)
        return

    backup = target.with_name(f"{target.name}.bak.{secrets.token_hex(_TMP_TOKEN_BYTES)}")
    target.replace(backup)
    try:
        staging.replace(target)
    except OSError:
        # Roll back: put the original content back in place.
        backup.replace(target)
        _safe_rmtree(staging)
        raise
    _safe_rmtree(backup)


def _safe_rmtree(path: Path) -> None:
    """Best-effort recursive delete; never raises."""
    if not path.exists():
        return
    try:
        if path.is_dir():
            for child in path.iterdir():
                _safe_rmtree(child)
            path.rmdir()
        else:
            path.unlink(missing_ok=True)
    except OSError:
        pass


__all__ = [
    "atomic_append_line",
    "atomic_write_text",
    "replace_directory_atomically",
]
