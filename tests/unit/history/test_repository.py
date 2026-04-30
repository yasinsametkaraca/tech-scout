"""Unit tests for the history repository."""

from __future__ import annotations

from pathlib import Path

import pytest

from tech_scout.domain.exceptions import HistoryLookupError
from tech_scout.history import HistoryRepository, list_history


def test_list_entries_returns_newest_first(fake_history_root: Path) -> None:
    entries = HistoryRepository(fake_history_root).list_entries()
    assert len(entries) == 2
    assert entries[0].folder_slug == "memory-layer-ai-agents"
    assert entries[1].folder_slug == "mcp-protocol-deep-dive"


def test_list_entries_extracts_title(fake_history_root: Path) -> None:
    entries = HistoryRepository(fake_history_root).list_entries()
    titles = {e.folder_slug: e.title for e in entries}
    assert "Memory Layer" in (titles["memory-layer-ai-agents"] or "")


def test_list_entries_extracts_primary_topic(fake_history_root: Path) -> None:
    entries = HistoryRepository(fake_history_root).list_entries()
    by_slug = {e.folder_slug: e for e in entries}
    mem = by_slug["memory-layer-ai-agents"]
    assert mem.primary_topic is not None
    assert "Mem0" in mem.primary_topic or "hafıza" in mem.primary_topic.lower()


def test_list_entries_extracts_primary_topic_for_english_package(
    english_history_root: Path,
) -> None:
    """Default-locale packages must surface their primary topic too.

    Regression test: the original implementation hardcoded the Turkish
    executive-summary filename, so English packages always returned a
    ``None`` primary_topic. The history repository now consults every
    registered locale's executive-summary filename.
    """
    entries = HistoryRepository(english_history_root).list_entries()
    by_slug = {e.folder_slug: e for e in entries}
    mem = by_slug["memory-layer-ai-agents"]
    assert mem.primary_topic is not None
    assert "Mem0" in mem.primary_topic
    mcp = by_slug["mcp-protocol-deep-dive"]
    assert mcp.primary_topic is not None
    assert "MCP" in mcp.primary_topic


def test_find_by_slug(fake_history_root: Path) -> None:
    repo = HistoryRepository(fake_history_root)
    found = repo.find_by_slug("memory-layer-ai-agents")
    assert found is not None
    assert found.folder_slug == "memory-layer-ai-agents"
    missing = repo.find_by_slug("does-not-exist")
    assert missing is None


def test_load_run_returns_files(fake_history_root: Path) -> None:
    repo = HistoryRepository(fake_history_root)
    run = repo.load_run("memory-layer-ai-agents")
    paths = {p.name for p in run.package_files}
    assert "README.md" in paths
    assert "00-yonetici-ozeti.md" in paths


def test_load_run_unknown_slug_raises(fake_history_root: Path) -> None:
    repo = HistoryRepository(fake_history_root)
    with pytest.raises(HistoryLookupError):
        repo.load_run("nope")


def test_nonexistent_root_returns_empty_list(tmp_path: Path) -> None:
    entries = HistoryRepository(tmp_path / "missing").list_entries()
    assert entries == []


def test_root_is_file_raises(tmp_path: Path) -> None:
    f = tmp_path / "file"
    f.write_text("not a dir")
    with pytest.raises(HistoryLookupError):
        HistoryRepository(f).list_entries()


def test_skips_undated_folders(tmp_path: Path) -> None:
    root = tmp_path / "research"
    root.mkdir()
    (root / "not-dated").mkdir()
    (root / "2026-04-22-real").mkdir()
    entries = list_history(root)
    assert len(entries) == 1
    assert entries[0].folder_slug == "real"
