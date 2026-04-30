"""Past research lookup.

Used by Phase 0 to detect when this week's likely topic overlaps with
prior weeks' work, so the LLM can either pick a different angle or
flag the overlap to the user.
"""

from __future__ import annotations

from tech_scout.history.deduplication import (
    OverlapDetector,
    detect_overlap,
)
from tech_scout.history.repository import HistoryRepository, list_history

__all__ = [
    "HistoryRepository",
    "OverlapDetector",
    "detect_overlap",
    "list_history",
]
