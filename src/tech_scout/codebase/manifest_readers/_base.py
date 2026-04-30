"""Abstract base for manifest readers.

A :class:`ManifestReader` answers two questions:

* "Is this file something I can read?" (:meth:`claims`)
* "What dependencies are declared in it?" (:meth:`read`)

Concrete readers live in sibling modules: ``python.py``, ``node.py``, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from tech_scout.domain.enums import StackKind


@dataclass(frozen=True, slots=True)
class ManifestDependency:
    """A single dependency entry parsed from a manifest."""

    name: str
    version: str | None = None
    kind: StackKind = StackKind.OTHER
    is_dev: bool = False


@dataclass(frozen=True, slots=True)
class ManifestReadResult:
    """The result of parsing a single manifest file."""

    manifest_path: Path
    ecosystem: str
    language: str
    language_version: str | None = None
    dependencies: tuple[ManifestDependency, ...] = field(default_factory=tuple)
    raw_metadata: dict[str, str] = field(default_factory=dict)


class ManifestReader(ABC):
    """Abstract reader for one ecosystem (Python, Node, Go, etc.)."""

    @property
    @abstractmethod
    def ecosystem(self) -> str:
        """Short identifier: 'python', 'node', 'go', etc."""

    @property
    @abstractmethod
    def language(self) -> str:
        """Human-readable language label: 'Python', 'JavaScript/TypeScript', etc."""

    @abstractmethod
    def claims(self, path: Path) -> bool:
        """Return True if this reader can parse *path*."""

    @abstractmethod
    def read(self, path: Path) -> ManifestReadResult:
        """Parse *path* and return its dependencies.

        Implementations must not raise on parse errors; instead, they should
        return a result with empty dependencies and a note in ``raw_metadata``.
        Hard errors (file unreadable, encoding garbled) may raise
        :class:`~tech_scout.domain.exceptions.CodebaseScanError`.
        """

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"
