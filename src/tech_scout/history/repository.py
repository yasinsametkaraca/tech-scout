"""Filesystem-backed repository of past research runs.

Convention: each prior run lives in its own subdirectory under a
research-documentation root, named ``YYYY-MM-DD-<slug>``. The directory
contains the rendered package (00- through README.md) plus an optional
``.tech-scout/state.json`` from the in-progress phase.

This module discovers those directories and produces lightweight
:class:`~tech_scout.domain.models.HistoryEntry` summaries without reading
the full content of every package.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from tech_scout.config.logging import get_logger
from tech_scout.domain.enums import OutputDocSlot
from tech_scout.domain.exceptions import HistoryLookupError
from tech_scout.domain.models import HistoryEntry, PriorRun
from tech_scout.locales import list_locales

log = get_logger(__name__)

_DATED_FOLDER = re.compile(r"^(\d{4}-\d{2}-\d{2})[-_](.+)$")
_TITLE_LINE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

_EXECUTIVE_SUMMARY_FILENAMES: tuple[str, ...] = tuple(
    spec.filename_for(OutputDocSlot.EXECUTIVE_SUMMARY) for spec in list_locales()
)


class HistoryRepository:
    """Read-only view of prior research run folders."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def list_entries(self) -> list[HistoryEntry]:
        """List prior runs, newest first.

        Returns an empty list if the root does not exist (a fresh user has
        no history yet — that's not an error).
        """
        if not self._root.exists():
            return []
        if not self._root.is_dir():
            msg = f"History root is not a directory: {self._root}"
            raise HistoryLookupError(msg, context={"root": str(self._root)})

        entries: list[HistoryEntry] = []
        for child in self._root.iterdir():
            if not child.is_dir():
                continue
            entry = self._build_entry(child)
            if entry is not None:
                entries.append(entry)

        entries.sort(
            key=lambda e: e.completed_date or date.min,
            reverse=True,
        )
        return entries

    def find_by_slug(self, slug: str) -> HistoryEntry | None:
        """Return the entry whose folder slug matches *slug*, if any."""
        for entry in self.list_entries():
            if entry.folder_slug == slug:
                return entry
        return None

    def load_run(self, slug: str) -> PriorRun:
        """Load detailed view of a prior run for ``/tech-scout-show``."""
        entry = self.find_by_slug(slug)
        if entry is None:
            msg = f"No prior run with slug: {slug}"
            raise HistoryLookupError(msg, context={"slug": slug})

        package_files = tuple(sorted(p for p in entry.folder_path.iterdir() if p.is_file()))
        return PriorRun(entry=entry, package_files=package_files)

    def _build_entry(self, folder: Path) -> HistoryEntry | None:
        match = _DATED_FOLDER.match(folder.name)
        if not match:
            log.debug("history_folder_skipped", path=str(folder), reason="not dated")
            return None

        completed_date_str, slug = match.groups()
        try:
            completed = date.fromisoformat(completed_date_str)
        except ValueError:
            log.debug("history_folder_skipped", path=str(folder), reason="bad date")
            return None

        exec_summary = _first_existing(folder, _EXECUTIVE_SUMMARY_FILENAMES)
        title = _read_title(folder / "README.md") or (
            _read_title(exec_summary) if exec_summary is not None else None
        )
        primary_topic = _read_first_paragraph(exec_summary) if exec_summary is not None else None

        return HistoryEntry(
            folder_path=folder,
            folder_slug=slug,
            title=title,
            primary_topic=primary_topic,
            completed_date=completed,
        )


def list_history(root: Path) -> list[HistoryEntry]:
    """Convenience for callers without DI needs."""
    return HistoryRepository(root).list_entries()


def _first_existing(folder: Path, names: Iterable[str]) -> Path | None:
    for name in names:
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


def _read_title(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _TITLE_LINE.search(text)
    if match:
        return match.group(1).strip()
    return None


_PARAGRAPH_LIMIT = 500


def _read_first_paragraph(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    lines = []
    started = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if started:
                break
            continue
        if line.startswith("#"):
            continue
        started = True
        lines.append(line)
    if not lines:
        return None
    paragraph = " ".join(lines)
    return paragraph[:_PARAGRAPH_LIMIT].strip() or None


def collect_topics(entries: Iterable[HistoryEntry]) -> list[str]:
    """Extract a flat list of recent topics for overlap detection."""
    topics: list[str] = []
    for e in entries:
        if e.primary_topic:
            topics.append(e.primary_topic)
        if e.title:
            topics.append(e.title)
    return topics
