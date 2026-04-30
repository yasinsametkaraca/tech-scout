"""Schema constants and helpers for run-state JSON files.

The state directory layout::

    <output-folder>/.tech-scout/<run-id>/
        state.json              # ResearchRequest + run metadata
        candidates.json         # Phase 3 output
        selection.json          # User pick after Stage A
        codebase-profile.json   # Phase 1 output (if codebase scanned)
        audit.jsonl             # Append-only event log
        phase-progress.json     # Phase status for resume

Filenames are constants so callers don't sprinkle string literals.
"""

from __future__ import annotations

from typing import Final

STATE_FILENAME: Final[str] = "state.json"
CANDIDATES_FILENAME: Final[str] = "candidates.json"
SELECTION_FILENAME: Final[str] = "selection.json"
CODEBASE_PROFILE_FILENAME: Final[str] = "codebase-profile.json"
AUDIT_FILENAME: Final[str] = "audit.jsonl"
PHASE_PROGRESS_FILENAME: Final[str] = "phase-progress.json"

STATE_DIR_NAME: Final[str] = ".tech-scout"
"""Directory under the output folder that holds per-run state."""

ALL_STATE_FILES: Final[tuple[str, ...]] = (
    STATE_FILENAME,
    CANDIDATES_FILENAME,
    SELECTION_FILENAME,
    CODEBASE_PROFILE_FILENAME,
    AUDIT_FILENAME,
    PHASE_PROGRESS_FILENAME,
)
