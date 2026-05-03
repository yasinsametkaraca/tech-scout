"""Cross-platform advisory file lock.

Used to serialize cross-process appenders to ``audit.jsonl`` so that
parallel analyzer subagents (Phase 4 spawns one per chosen candidate) do
not interleave partial JSON lines. Within a single process,
:class:`tech_scout.observability.audit_log.AuditLogger` already takes a
:class:`threading.Lock`; this module covers the multi-process case.

The implementation uses ``msvcrt.locking`` on Windows and ``fcntl.flock``
on POSIX. Both are advisory — they cooperate only with other code that
uses the same mechanism. We have no need for mandatory locking; every
audit-log writer in this codebase routes through :class:`FileLock`.

Usage::

    with FileLock(path / ".audit.lock", timeout_seconds=10.0):
        # do the cross-process-protected work
        ...
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import suppress
from pathlib import Path
from types import TracebackType

if sys.platform == "win32":  # pragma: no cover - branch tested on Windows only
    import msvcrt
else:  # pragma: no cover - branch tested on POSIX only
    import fcntl


class FileLockTimeoutError(TimeoutError):
    """Raised when :class:`FileLock` cannot acquire within its timeout."""


class FileLock:
    """A blocking, cross-platform advisory file lock with timeout.

    Re-entrant within the same process (a thread that already holds the
    lock can re-enter without blocking). Across processes, the lock is
    exclusive: only one holder at a time.

    The lock file itself is created lazily and never deleted — keeping it
    around avoids a race where one process unlinks the file between two
    others' open + lock calls. The file's contents are never read or
    written; only its file descriptor is locked.
    """

    def __init__(
        self,
        path: Path,
        *,
        timeout_seconds: float = 10.0,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        if timeout_seconds <= 0:
            msg = f"timeout_seconds must be > 0, got {timeout_seconds}"
            raise ValueError(msg)
        if poll_interval_seconds <= 0:
            msg = f"poll_interval_seconds must be > 0, got {poll_interval_seconds}"
            raise ValueError(msg)
        self._path = Path(path)
        self._timeout = timeout_seconds
        self._poll = poll_interval_seconds
        self._fd: int | None = None
        self._depth = 0

    @property
    def path(self) -> Path:
        return self._path

    def acquire(self) -> None:
        if self._fd is not None:
            self._depth += 1
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o644)
        acquired = False
        try:
            deadline = time.monotonic() + self._timeout
            while True:
                try:
                    _platform_lock(fd)
                except (BlockingIOError, OSError):
                    if time.monotonic() >= deadline:
                        msg = (
                            f"Could not acquire file lock {self._path} within {self._timeout:.1f}s"
                        )
                        raise FileLockTimeoutError(msg) from None
                    time.sleep(self._poll)
                    continue
                else:
                    self._fd = fd
                    self._depth = 1
                    acquired = True
                    return
        finally:
            if not acquired:
                # The lock either timed out or the loop was interrupted (e.g.
                # KeyboardInterrupt). Either way, the fd is ours to clean up.
                with suppress(OSError):
                    os.close(fd)

    def release(self) -> None:
        if self._fd is None:
            return
        self._depth -= 1
        if self._depth > 0:
            return
        try:
            _platform_unlock(self._fd)
        finally:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
                self._depth = 0

    def __enter__(self) -> FileLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


if sys.platform == "win32":  # pragma: no cover - tested on Windows only

    def _platform_lock(fd: int) -> None:
        # Lock 1 byte starting at offset 0; non-blocking. Raises OSError on
        # contention so the caller's polling loop can retry.
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _platform_unlock(fd: int) -> None:
        # Seek to byte 0 to match the locked region before unlocking.
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:  # pragma: no cover - tested on POSIX only

    def _platform_lock(fd: int) -> None:
        # Exclusive non-blocking lock; raises BlockingIOError on contention.
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _platform_unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


__all__ = ["FileLock", "FileLockTimeoutError"]
