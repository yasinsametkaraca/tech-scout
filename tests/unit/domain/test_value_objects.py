"""Unit tests for domain value objects."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from tech_scout.domain.value_objects import (
    OutputPath,
    RunId,
    Slug,
    SourceRef,
    TimeWindow,
)


class TestRunId:
    def test_valid_format_accepted(self) -> None:
        run = RunId(value="2026-04-29-abc123")
        assert run.value == "2026-04-29-abc123"
        assert run.slug_part == "abc123"
        assert run.date_part.isoformat() == "2026-04-29"

    def test_str_returns_value(self) -> None:
        run = RunId(value="2026-04-29-xyz789")
        assert str(run) == "2026-04-29-xyz789"

    @pytest.mark.parametrize(
        "bad_value",
        [
            "no-date",
            "2026-04-29-AB",  # uppercase
            "2026-04-29-abc",  # too short slug
            "2026-04-29-abcdefghijklmnop",  # too long slug
            "2026-4-29-abc123",  # bad date format
            "2026-04-29",  # missing slug
        ],
    )
    def test_invalid_format_rejected(self, bad_value: str) -> None:
        with pytest.raises(ValidationError):
            RunId(value=bad_value)

    def test_run_id_is_frozen(self) -> None:
        run = RunId(value="2026-04-29-abc123")
        with pytest.raises(ValidationError):
            run.value = "2026-04-30-def456"  # type: ignore[misc]


class TestTimeWindow:
    def test_end_after_start_accepted(self) -> None:
        start = datetime(2026, 4, 22, tzinfo=timezone.utc)
        end = datetime(2026, 4, 29, tzinfo=timezone.utc)
        tw = TimeWindow(start=start, end=end)
        assert tw.days() == 7

    def test_end_before_start_rejected(self) -> None:
        start = datetime(2026, 4, 29, tzinfo=timezone.utc)
        end = datetime(2026, 4, 22, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            TimeWindow(start=start, end=end)

    def test_end_equals_start_rejected(self) -> None:
        ts = datetime(2026, 4, 29, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            TimeWindow(start=ts, end=ts)

    def test_last_n_days_factory(self) -> None:
        now = datetime(2026, 4, 29, 10, 0, 0, tzinfo=timezone.utc)
        tw = TimeWindow.last_n_days(7, now=now)
        assert tw.end == now.replace(microsecond=0)
        assert tw.start == now.replace(microsecond=0) - timedelta(days=7)


class TestSourceRef:
    def test_minimum_fields(self) -> None:
        ref = SourceRef(
            url="https://arxiv.org/abs/2603.03329",
            title="AutoHarness paper",
        )
        assert str(ref.url).rstrip("/") == "https://arxiv.org/abs/2603.03329"
        assert ref.title == "AutoHarness paper"
        assert ref.publication_date is None

    def test_invalid_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SourceRef(url="not-a-url", title="Test")

    def test_empty_title_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SourceRef(url="https://example.com", title="")


class TestSlug:
    def test_valid_slug_accepted(self) -> None:
        slug = Slug(value="memory-layer-ai-agents")
        assert str(slug) == "memory-layer-ai-agents"

    @pytest.mark.parametrize(
        "bad_value",
        [
            "Memory-Layer",  # uppercase
            "double--hyphen",  # double hyphen
            "-leading-hyphen",
            "trailing-hyphen-",
            "with space",
            "with_underscore",
            "",
        ],
    )
    def test_invalid_slug_rejected(self, bad_value: str) -> None:
        with pytest.raises(ValidationError):
            Slug(value=bad_value)


class TestOutputPath:
    def test_existing_directory_accepted(self, tmp_path: Path) -> None:
        op = OutputPath(path=tmp_path)
        assert op.path == tmp_path

    def test_nonexistent_with_existing_parent_accepted(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "new"
        op = OutputPath(path=new_dir)
        assert op.path == new_dir

    def test_nonexistent_parent_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "missing-parent" / "child"
        with pytest.raises(ValidationError):
            OutputPath(path=bad)
