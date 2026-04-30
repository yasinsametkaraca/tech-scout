"""Codebase analysis — scan a directory and infer the technology stack.

Used by Phase 1 of the research pipeline. The skill calls
``ts_scan_codebase.py`` (which uses this package) to produce a
:class:`~tech_scout.domain.models.CodebaseProfile` JSON document.

Public API:

* :func:`scan_codebase` — top-level entry point
* :class:`CodebaseScanner` — class form (for dependency injection in tests)
"""

from __future__ import annotations

from tech_scout.codebase.architecture_summary import (
    ArchitectureSummarizer,
    summarize_architecture,
)
from tech_scout.codebase.scanner import CodebaseScanner, scan_codebase
from tech_scout.codebase.stack_detector import StackDetector, detect_stack

__all__ = [
    "ArchitectureSummarizer",
    "CodebaseScanner",
    "StackDetector",
    "detect_stack",
    "scan_codebase",
    "summarize_architecture",
]
