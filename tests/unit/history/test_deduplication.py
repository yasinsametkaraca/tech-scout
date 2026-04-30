"""Unit tests for topic-overlap detection."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from tech_scout.domain.models import HistoryEntry
from tech_scout.history import OverlapDetector, detect_overlap


def _entry(slug: str, title: str, topic: str) -> HistoryEntry:
    return HistoryEntry(
        folder_path=Path(f"/tmp/{slug}"),
        folder_slug=slug,
        title=title,
        primary_topic=topic,
        completed_date=date(2026, 4, 22),
    )


def test_detects_strong_overlap() -> None:
    entries = [
        _entry(
            "memory-layer",
            "Memory Layer for AI Agents Mem0 Letta",
            "Memory layer architectures Mem0 Letta agents.",
        )
    ]
    hits = detect_overlap(
        candidate_text="Memory Layer Architectures Mem0 Letta",
        history_entries=entries,
    )
    assert len(hits) == 1
    assert hits[0].similarity >= 0.4
    assert "memory" in hits[0].matched_tokens
    assert "letta" in hits[0].matched_tokens


def test_no_overlap_returns_empty() -> None:
    entries = [
        _entry(
            "voice-ai",
            "Voice AI Roundup",
            "ElevenLabs, Cartesia, Deepgram speech synthesis updates.",
        )
    ]
    hits = detect_overlap(
        candidate_text="MCP Protocol Standardization Efforts",
        history_entries=entries,
    )
    assert hits == []


def test_threshold_filters_weak_matches() -> None:
    entries = [
        _entry(
            "abc",
            "ABC Topic",
            "Some unrelated content with one shared word: agent.",
        )
    ]
    detector = OverlapDetector(similarity_threshold=0.6)
    hits = detector.find_overlaps(
        candidate_text="Different topic about agents and tools",
        history_entries=entries,
    )
    assert hits == []


def test_invalid_threshold_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        OverlapDetector(similarity_threshold=0.0)
    with pytest.raises(ValueError):
        OverlapDetector(similarity_threshold=1.5)


def test_empty_text_returns_no_hits() -> None:
    entries = [_entry("x", "X", "X content here")]
    assert detect_overlap("", entries) == []
