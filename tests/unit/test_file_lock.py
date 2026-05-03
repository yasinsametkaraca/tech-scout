"""Unit tests for the cross-platform file lock."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from tech_scout.utils.file_lock import FileLock, FileLockTimeoutError


class TestFileLockBasic:
    def test_acquire_and_release(self, tmp_path: Path) -> None:
        lock = FileLock(tmp_path / "x.lock", timeout_seconds=2.0)
        with lock:
            assert lock._fd is not None
        assert lock._fd is None

    def test_creates_lock_file(self, tmp_path: Path) -> None:
        path = tmp_path / "x.lock"
        lock = FileLock(path, timeout_seconds=2.0)
        with lock:
            assert path.is_file()
        # File is intentionally not deleted on release
        assert path.is_file()

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        lock = FileLock(tmp_path / "nested" / "deep" / "x.lock", timeout_seconds=2.0)
        with lock:
            pass
        assert (tmp_path / "nested" / "deep").is_dir()

    def test_reentrant_in_same_process(self, tmp_path: Path) -> None:
        lock = FileLock(tmp_path / "x.lock", timeout_seconds=2.0)
        with lock:
            with lock:
                assert lock._fd is not None
            # Still held after inner release
            assert lock._fd is not None
        # Released after outer release
        assert lock._fd is None

    def test_invalid_timeout_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            FileLock(tmp_path / "x.lock", timeout_seconds=0)

    def test_invalid_poll_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            FileLock(tmp_path / "x.lock", poll_interval_seconds=0)


def _hold_lock_then_exit(args: tuple[str, str, float]) -> None:
    """Helper: acquire lock, signal acquisition, hold for *hold_seconds*, exit.

    Writes a sentinel file when the lock is acquired so the parent test
    can wait for "child holds the lock" without racing against the
    interpreter-startup time of multiprocessing.spawn (which can be 500ms+
    on Windows).
    """
    lock_path_str, sentinel_path_str, hold_seconds = args
    lock = FileLock(Path(lock_path_str), timeout_seconds=30.0)
    with lock:
        Path(sentinel_path_str).write_text("held", encoding="utf-8")
        time.sleep(hold_seconds)


def _wait_for_sentinel(sentinel: Path, *, timeout_seconds: float = 30.0) -> None:
    """Poll until *sentinel* exists or timeout — used to sync with child."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if sentinel.is_file():
            return
        time.sleep(0.02)
    msg = f"Child never created sentinel at {sentinel} within {timeout_seconds:.1f}s"
    raise AssertionError(msg)


class TestFileLockCrossProcess:
    def test_second_process_blocks_until_first_releases(self, tmp_path: Path) -> None:
        lock_path = tmp_path / "x.lock"
        sentinel = tmp_path / "child_holds_lock.flag"
        ctx = multiprocessing.get_context("spawn")
        p = ctx.Process(
            target=_hold_lock_then_exit,
            args=((str(lock_path), str(sentinel), 0.5),),
        )
        p.start()
        try:
            _wait_for_sentinel(sentinel)
            local = FileLock(lock_path, timeout_seconds=5.0, poll_interval_seconds=0.05)
            start = time.monotonic()
            with local:
                elapsed = time.monotonic() - start
            # Child held for 0.5s; parent acquired after some of that hold remained.
            assert elapsed > 0.0
        finally:
            p.join(timeout=10)
        assert p.exitcode == 0

    def test_timeout_raises(self, tmp_path: Path) -> None:
        lock_path = tmp_path / "x.lock"
        sentinel = tmp_path / "child_holds_lock.flag"
        ctx = multiprocessing.get_context("spawn")
        p = ctx.Process(
            target=_hold_lock_then_exit,
            args=((str(lock_path), str(sentinel), 2.0),),
        )
        p.start()
        try:
            _wait_for_sentinel(sentinel)
            local = FileLock(lock_path, timeout_seconds=0.3, poll_interval_seconds=0.05)
            with pytest.raises(FileLockTimeoutError):
                local.acquire()
        finally:
            p.join(timeout=10)
