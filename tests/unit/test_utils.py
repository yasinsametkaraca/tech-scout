"""Unit tests for utils package."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from tech_scout.utils.path_safety import (
    ensure_directory,
    is_within_directory,
    normalize_path,
    safe_relative_path,
    windows_to_posix,
)
from tech_scout.utils.time import (
    humanize_minutes,
    iso_now,
    iso_today,
    parse_iso_date,
    parse_iso_datetime,
)
from tech_scout.utils.toml_compat import TOMLDecodeError, load, loads


class TestPathSafety:
    def test_normalize_resolves(self, tmp_path: Path) -> None:
        relative = tmp_path / ".." / tmp_path.name
        normalized = normalize_path(relative)
        assert normalized == tmp_path

    def test_is_within_directory_true(self, tmp_path: Path) -> None:
        child = tmp_path / "child"
        child.mkdir()
        assert is_within_directory(child, tmp_path)

    def test_is_within_directory_false(self, tmp_path: Path) -> None:
        sibling = tmp_path.parent
        assert not is_within_directory(sibling, tmp_path)

    def test_is_within_directory_handles_strings(self, tmp_path: Path) -> None:
        child = tmp_path / "x"
        child.mkdir()
        assert is_within_directory(str(child), str(tmp_path))

    def test_safe_relative_path(self, tmp_path: Path) -> None:
        child = tmp_path / "subdir" / "file.txt"
        child.parent.mkdir()
        child.write_text("x")
        rel = safe_relative_path(child, tmp_path)
        assert str(rel) == "subdir/file.txt"

    def test_safe_relative_path_traversal_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            safe_relative_path(tmp_path.parent, tmp_path)

    def test_ensure_directory_creates(self, tmp_path: Path) -> None:
        target = tmp_path / "new" / "nested" / "dir"
        result = ensure_directory(target)
        assert result.is_dir()

    def test_ensure_directory_idempotent(self, tmp_path: Path) -> None:
        ensure_directory(tmp_path / "a")
        ensure_directory(tmp_path / "a")  # No raise

    def test_ensure_directory_existing_file_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "file"
        f.write_text("x")
        with pytest.raises(OSError):
            ensure_directory(f)

    def test_windows_to_posix_drive_letter(self) -> None:
        out = windows_to_posix(r"C:\foo\bar")
        # On Windows: /c/foo/bar; on POSIX systems: just slash conversion
        assert "/" in out
        assert "\\" not in out

    def test_windows_to_posix_no_drive(self) -> None:
        out = windows_to_posix("foo/bar")
        assert out == "foo/bar"


class TestTimeUtils:
    def test_iso_now_default_utc(self) -> None:
        s = iso_now()
        # Either +00:00 suffix or Z form
        assert "T" in s

    def test_iso_now_naive(self) -> None:
        s = iso_now(naive=True)
        assert "T" in s
        assert "+" not in s

    def test_iso_today(self) -> None:
        s = iso_today()
        assert len(s) == 10  # YYYY-MM-DD
        assert s.count("-") == 2

    def test_parse_iso_datetime_z_suffix(self) -> None:
        dt = parse_iso_datetime("2026-04-29T10:30:00Z")
        assert dt.year == 2026
        assert dt.tzinfo is not None

    def test_parse_iso_datetime_offset(self) -> None:
        dt = parse_iso_datetime("2026-04-29T10:30:00+00:00")
        assert dt.year == 2026

    def test_parse_iso_date(self) -> None:
        d = parse_iso_date("2026-04-29")
        assert d.year == 2026
        assert d.month == 4
        assert d.day == 29

    def test_humanize_minutes_under_hour(self) -> None:
        assert humanize_minutes(45) == "45m"
        assert humanize_minutes(0) == "0m"

    def test_humanize_minutes_exact_hours(self) -> None:
        assert humanize_minutes(60) == "1h"
        assert humanize_minutes(120) == "2h"

    def test_humanize_minutes_with_remainder(self) -> None:
        assert humanize_minutes(90) == "1h 30m"
        assert humanize_minutes(135) == "2h 15m"

    def test_humanize_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            humanize_minutes(-5)


class TestTomlCompat:
    def test_loads_simple_table(self) -> None:
        out = loads('[project]\nname = "x"\n')
        assert out == {"project": {"name": "x"}}

    def test_loads_invalid_raises(self) -> None:
        with pytest.raises(TOMLDecodeError):
            loads("not = valid = toml")

    def test_load_from_binary_stream(self) -> None:
        buf = io.BytesIO(b"[tool.x]\nflag = true\n")
        out = load(buf)
        assert out == {"tool": {"x": {"flag": True}}}

    def test_loads_returns_native_python_types(self) -> None:
        out = loads('name = "demo"\nversion = 2\nenabled = true\ntags = ["a", "b"]\n')
        assert out == {"name": "demo", "version": 2, "enabled": True, "tags": ["a", "b"]}
