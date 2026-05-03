"""Unit tests for atomic filesystem helpers."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tech_scout.utils.atomic_io import (
    atomic_append_line,
    atomic_write_text,
    replace_directory_atomically,
)


class TestAtomicWriteText:
    def test_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        atomic_write_text(target, '{"x": 1}\n')
        assert target.read_text(encoding="utf-8") == '{"x": 1}\n'

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        target.write_text("old", encoding="utf-8")
        atomic_write_text(target, "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "deep" / "out.json"
        atomic_write_text(target, "x")
        assert target.is_file()

    def test_no_temp_file_left_after_success(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        atomic_write_text(target, "x")
        siblings = [p.name for p in tmp_path.iterdir()]
        # Only the final file should remain — no .tmp.* leftovers
        assert siblings == ["out.json"]

    def test_failure_during_replace_preserves_original(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        target.write_text("ORIGINAL", encoding="utf-8")

        # Force os.replace to fail by mocking Path.replace globally.
        original_replace = Path.replace

        def boom(self: Path, *_args: object, **_kwargs: object) -> Path:
            if self.name.startswith("out.json.tmp."):
                raise OSError("simulated failure")
            return original_replace(self, *_args, **_kwargs)

        with patch.object(Path, "replace", boom), pytest.raises(OSError, match="simulated"):
            atomic_write_text(target, "NEW")

        # Original content survives because the rename failed.
        assert target.read_text(encoding="utf-8") == "ORIGINAL"
        # And the temp file was cleaned up.
        leftovers = [p for p in tmp_path.iterdir() if ".tmp." in p.name]
        assert leftovers == []

    def test_unicode_content(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        atomic_write_text(target, "ışık şehir gözü 🌟")
        assert target.read_text(encoding="utf-8") == "ışık şehir gözü 🌟"


class TestAtomicAppendLine:
    def test_appends_lines(self, tmp_path: Path) -> None:
        target = tmp_path / "log.jsonl"
        atomic_append_line(target, "line1")
        atomic_append_line(target, "line2")
        assert target.read_text(encoding="utf-8").splitlines() == ["line1", "line2"]

    def test_adds_trailing_newline_when_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "log.jsonl"
        atomic_append_line(target, "no-newline")
        text = target.read_text(encoding="utf-8")
        assert text.endswith("\n")

    def test_preserves_provided_newline(self, tmp_path: Path) -> None:
        target = tmp_path / "log.jsonl"
        atomic_append_line(target, "with-newline\n")
        # Should not double-up
        assert target.read_text(encoding="utf-8") == "with-newline\n"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "log.jsonl"
        atomic_append_line(target, "x")
        assert target.is_file()


class TestReplaceDirectoryAtomically:
    def test_creates_target_when_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        with replace_directory_atomically(target) as staging:
            (staging / "a.txt").write_text("hello", encoding="utf-8")
        assert (target / "a.txt").read_text(encoding="utf-8") == "hello"

    def test_replaces_existing_target(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (target / "old.txt").write_text("old", encoding="utf-8")
        with replace_directory_atomically(target) as staging:
            (staging / "new.txt").write_text("new", encoding="utf-8")
        names = sorted(p.name for p in target.iterdir())
        assert names == ["new.txt"]

    def test_exception_inside_block_preserves_target(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (target / "keep.txt").write_text("keep", encoding="utf-8")

        def _do_work() -> None:
            with replace_directory_atomically(target) as staging:
                (staging / "wont_persist.txt").write_text("x", encoding="utf-8")
                raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            _do_work()

        names = sorted(p.name for p in target.iterdir())
        assert names == ["keep.txt"]
        # No staging dirs leaked at the parent level
        leftovers = [p.name for p in tmp_path.iterdir() if "staging" in p.name]
        assert leftovers == []

    def test_no_backup_left_after_success(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (target / "old.txt").write_text("old", encoding="utf-8")
        with replace_directory_atomically(target) as staging:
            (staging / "new.txt").write_text("new", encoding="utf-8")
        leftovers = [
            p.name for p in tmp_path.iterdir() if ".bak." in p.name or ".staging." in p.name
        ]
        assert leftovers == []


class TestPermissions:
    def test_written_file_readable(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        atomic_write_text(target, "x")
        # Should be readable with default umask
        assert os.access(target, os.R_OK)
