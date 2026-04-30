"""Manifest readers — one per ecosystem.

Each reader implements :class:`~tech_scout.codebase.manifest_readers._base.ManifestReader`
and knows how to identify and parse a specific dependency manifest format.
The :class:`~tech_scout.codebase.scanner.CodebaseScanner` walks the directory
tree and dispatches files to whichever reader claims them.

To add a new ecosystem:

1. Create ``<ecosystem>.py`` here.
2. Subclass :class:`ManifestReader`.
3. Add it to :data:`DEFAULT_READERS` below.

The order in :data:`DEFAULT_READERS` matters only for tie-breaking — readers
should not overlap, but if they do, the earlier one wins.
"""

from __future__ import annotations

from tech_scout.codebase.manifest_readers._base import ManifestReader, ManifestReadResult
from tech_scout.codebase.manifest_readers.dotnet import DotNetManifestReader
from tech_scout.codebase.manifest_readers.go import GoManifestReader
from tech_scout.codebase.manifest_readers.java import JavaManifestReader
from tech_scout.codebase.manifest_readers.node import NodeManifestReader
from tech_scout.codebase.manifest_readers.python import PythonManifestReader
from tech_scout.codebase.manifest_readers.rust import RustManifestReader

DEFAULT_READERS: tuple[type[ManifestReader], ...] = (
    PythonManifestReader,
    NodeManifestReader,
    GoManifestReader,
    RustManifestReader,
    JavaManifestReader,
    DotNetManifestReader,
)

__all__ = [
    "DEFAULT_READERS",
    "DotNetManifestReader",
    "GoManifestReader",
    "JavaManifestReader",
    "ManifestReadResult",
    "ManifestReader",
    "NodeManifestReader",
    "PythonManifestReader",
    "RustManifestReader",
]
