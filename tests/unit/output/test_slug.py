"""Unit tests for slug generation."""

from __future__ import annotations

from datetime import date

import pytest

from tech_scout.output.slug import (
    build_output_folder_name,
    build_run_id,
    slugify_topic,
    unique_run_slug,
)


class TestSlugifyTopic:
    def test_basic_english(self) -> None:
        slug = slugify_topic("Memory Layer for AI Agents")
        assert str(slug) == "memory-layer-for-ai-agents"

    def test_turkish_chars_transliterated(self) -> None:
        slug = slugify_topic("Şirket içi gözlemleme ve değerlendirme")
        s = str(slug)
        assert "ş" not in s
        assert "ç" not in s
        assert "ğ" not in s
        assert "ı" not in s
        assert "ö" not in s
        assert s.startswith("sirket")

    def test_em_dash_handled(self) -> None:
        slug = slugify_topic("MCP — Model Context Protocol")
        assert "—" not in str(slug)
        assert "mcp" in str(slug)

    def test_max_length(self) -> None:
        long = "x" * 200
        slug = slugify_topic(long, max_length=20)
        assert len(str(slug)) <= 20

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            slugify_topic("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError):
            slugify_topic("   \t\n  ")


class TestUniqueRunSlug:
    def test_default_length(self) -> None:
        s = unique_run_slug()
        assert len(s) == 8
        assert s.isalnum() and s.islower()

    def test_custom_length(self) -> None:
        s = unique_run_slug(length=10)
        assert len(s) == 10

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError):
            unique_run_slug(length=4)

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError):
            unique_run_slug(length=20)

    def test_two_calls_differ(self) -> None:
        # Vanishingly small chance of collision
        a = unique_run_slug()
        b = unique_run_slug()
        assert a != b


class TestBuildRunId:
    def test_uses_today(self, frozen_today: date) -> None:
        rid = build_run_id(today=frozen_today)
        assert str(rid).startswith("2026-04-29-")
        assert rid.date_part == frozen_today


class TestBuildOutputFolderName:
    def test_with_slug_object(self, frozen_today: date) -> None:
        slug = slugify_topic("Memory Layer")
        name = build_output_folder_name(today=frozen_today, topic_slug=slug)
        assert name == "2026-04-29-memory-layer"

    def test_with_string(self, frozen_today: date) -> None:
        name = build_output_folder_name(today=frozen_today, topic_slug="x-y-z")
        assert name == "2026-04-29-x-y-z"
