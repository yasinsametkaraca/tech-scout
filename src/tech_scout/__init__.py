"""tech-scout: Claude Code-native plugin for weekly tech research.

This package provides the Python helper library that the Claude Code plugin
(in `.claude/`) calls via Bash to perform deterministic work — manifest
reading, slug generation, Jinja2 rendering, state persistence, validation.

The package is intentionally small: the orchestration intelligence lives in
the Claude Code skill, not here. See `docs/architecture.md`.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
