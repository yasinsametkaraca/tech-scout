"""Topic-overlap detection.

Cheap, deterministic: lowercased token-set Jaccard similarity. The point
isn't perfect dedup; it's a hint to the LLM ("look, last week was about X
— pick a different angle this time").

For semantic similarity we'd want embeddings, but that adds dependencies
and an API call. The token-set approach catches the common case
(repeating a near-identical title) and is good enough for a hint.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from tech_scout.domain.models import HistoryEntry

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "or",
        "the",
        "of",
        "for",
        "with",
        "to",
        "in",
        "on",
        "by",
        "is",
        "are",
        "be",
        "was",
        "were",
        "ile",
        "ve",
        "veya",
        "icin",
        "için",
        "bir",
        "bu",
        "ama",
        "ne",
        "ya",
    }
)


@dataclass(frozen=True, slots=True)
class OverlapHit:
    """One matched prior entry with similarity score."""

    entry: HistoryEntry
    similarity: float
    matched_tokens: tuple[str, ...]


class OverlapDetector:
    """Detect token-set overlap between a candidate topic and prior runs.

    Threshold defaults to 0.4 — anything above that is reported. Tune via
    the constructor for different sensitivity.
    """

    def __init__(self, *, similarity_threshold: float = 0.4) -> None:
        if not 0.0 < similarity_threshold <= 1.0:
            msg = f"similarity_threshold must be in (0, 1]: {similarity_threshold}"
            raise ValueError(msg)
        self._threshold = similarity_threshold

    def find_overlaps(
        self,
        candidate_text: str,
        history_entries: Iterable[HistoryEntry],
    ) -> list[OverlapHit]:
        cand_tokens = _tokenize(candidate_text)
        if not cand_tokens:
            return []

        hits: list[OverlapHit] = []
        for entry in history_entries:
            entry_text = " ".join(filter(None, [entry.title, entry.primary_topic]))
            entry_tokens = _tokenize(entry_text)
            if not entry_tokens:
                continue
            jaccard, common = _jaccard_with_overlap(cand_tokens, entry_tokens)
            if jaccard >= self._threshold:
                hits.append(
                    OverlapHit(
                        entry=entry,
                        similarity=jaccard,
                        matched_tokens=tuple(sorted(common)),
                    )
                )
        hits.sort(key=lambda h: h.similarity, reverse=True)
        return hits


def detect_overlap(
    candidate_text: str,
    history_entries: Iterable[HistoryEntry],
    *,
    threshold: float = 0.4,
) -> list[OverlapHit]:
    """Convenience function with default detector configuration."""
    return OverlapDetector(similarity_threshold=threshold).find_overlaps(
        candidate_text=candidate_text,
        history_entries=history_entries,
    )


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    tokens = {t for t in _TOKEN.findall(text.lower()) if len(t) > 2}
    return tokens - _STOPWORDS


def _jaccard_with_overlap(a: set[str], b: set[str]) -> tuple[float, set[str]]:
    if not a or not b:
        return 0.0, set()
    intersection = a & b
    union = a | b
    return len(intersection) / len(union), intersection
