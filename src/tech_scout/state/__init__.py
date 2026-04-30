"""Run state persistence.

State files live under ``<output-folder>/.tech-scout/<run-id>/`` and persist
across the gap between Stage A (scan + shortlist) and Stage B (deep + render).
This is what lets the user resume a run after closing the terminal.

Public API:

* :class:`StateStore` — read/write JSON state files
* schema constants — :data:`STATE_FILENAME`, :data:`CANDIDATES_FILENAME`, etc.
"""

from __future__ import annotations

from tech_scout.state.schemas import (
    AUDIT_FILENAME,
    CANDIDATES_FILENAME,
    CODEBASE_PROFILE_FILENAME,
    PHASE_PROGRESS_FILENAME,
    SELECTION_FILENAME,
    STATE_FILENAME,
)
from tech_scout.state.store import StateStore

__all__ = [
    "AUDIT_FILENAME",
    "CANDIDATES_FILENAME",
    "CODEBASE_PROFILE_FILENAME",
    "PHASE_PROGRESS_FILENAME",
    "SELECTION_FILENAME",
    "STATE_FILENAME",
    "StateStore",
]
