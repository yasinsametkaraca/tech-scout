"""Codebase scanner.

Walks a directory tree, identifies manifest files, dispatches them to the
right :class:`ManifestReader`, and returns a :class:`CodebaseProfile`.

The scanner is intentionally cautious: it never executes code, never
follows symlinks outside the root, and bounds its traversal depth and
file count to protect against pathological inputs.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from tech_scout.codebase.architecture_summary import (
    ArchitectureSummarizer,
)
from tech_scout.codebase.manifest_readers import DEFAULT_READERS
from tech_scout.codebase.manifest_readers._base import ManifestReader, ManifestReadResult
from tech_scout.codebase.stack_detector import StackDetector
from tech_scout.config.logging import get_logger
from tech_scout.domain.exceptions import CodebaseScanError
from tech_scout.domain.models import CodebaseProfile

log = get_logger(__name__)


_IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "out",
        "target",
        ".next",
        ".nuxt",
        ".turbo",
        ".tech-scout",
        ".idea",
        ".vscode",
        ".cache",
        "coverage",
        "htmlcov",
        ".tox",
    }
)


@dataclass(frozen=True, slots=True)
class ScannerConfig:
    """Tuning parameters for the scanner."""

    max_depth: int = 8
    max_files_visited: int = 50_000
    max_manifest_files: int = 500
    follow_symlinks: bool = False
    ignored_dirs: frozenset[str] = field(default_factory=lambda: _IGNORED_DIRS)


class CodebaseScanner:
    """Walk a codebase and produce a :class:`CodebaseProfile`.

    Composed of:

    * a list of :class:`ManifestReader` instances (one per ecosystem)
    * a :class:`StackDetector` that maps manifests to stack entries
    * an :class:`ArchitectureSummarizer` that infers high-level facts

    All collaborators are injected for testability.
    """

    def __init__(
        self,
        readers: Iterable[ManifestReader] | None = None,
        *,
        stack_detector: StackDetector | None = None,
        summarizer: ArchitectureSummarizer | None = None,
        config: ScannerConfig | None = None,
    ) -> None:
        self._readers: tuple[ManifestReader, ...] = tuple(
            readers if readers is not None else (cls() for cls in DEFAULT_READERS)
        )
        self._stack_detector = stack_detector or StackDetector()
        self._summarizer = summarizer or ArchitectureSummarizer()
        self._config = config or ScannerConfig()

    def scan(self, root: Path) -> CodebaseProfile:
        if not root.exists():
            msg = f"Codebase root does not exist: {root}"
            raise CodebaseScanError(msg, context={"root": str(root)})
        if not root.is_dir():
            msg = f"Codebase root is not a directory: {root}"
            raise CodebaseScanError(msg, context={"root": str(root)})

        log.info("codebase_scan_started", root=str(root))

        manifest_results: list[ManifestReadResult] = []
        files_visited = 0
        for manifest_path in self._walk(root):
            files_visited += 1
            if files_visited > self._config.max_files_visited:
                log.warning(
                    "scan_file_limit_reached",
                    limit=self._config.max_files_visited,
                )
                break
            if len(manifest_results) >= self._config.max_manifest_files:
                log.warning(
                    "scan_manifest_limit_reached",
                    limit=self._config.max_manifest_files,
                )
                break

            reader = self._reader_for(manifest_path)
            if reader is None:
                continue
            try:
                result = reader.read(manifest_path)
            except CodebaseScanError as exc:
                log.warning(
                    "manifest_read_failed",
                    path=str(manifest_path),
                    error=str(exc),
                )
                continue
            manifest_results.append(result)

        log.info(
            "codebase_scan_completed",
            root=str(root),
            manifests_found=len(manifest_results),
            files_visited=files_visited,
        )

        readme_excerpt = _read_excerpt(root / "README.md") or _read_excerpt(root / "readme.md")

        entries = self._stack_detector.detect(manifest_results)
        architecture = self._summarizer.summarize(
            root=root,
            entries=entries,
            manifest_results=manifest_results,
            readme=readme_excerpt,
        )

        return CodebaseProfile(
            root_path=root,
            entries=tuple(entries),
            architecture=architecture,
            readme_excerpt=readme_excerpt,
            manifest_files_found=tuple(
                str(r.manifest_path.relative_to(root)) for r in manifest_results
            ),
        )

    def _walk(self, root: Path) -> Iterator[Path]:
        """Yield candidate manifest files, depth-limited and ignore-aware."""
        ignored = self._config.ignored_dirs
        max_depth = self._config.max_depth

        stack: list[tuple[Path, int]] = [(root, 0)]
        while stack:
            current, depth = stack.pop()
            if depth > max_depth:
                continue
            try:
                children = list(current.iterdir())
            except (PermissionError, OSError) as exc:
                log.debug("directory_unreadable", path=str(current), error=str(exc))
                continue
            for child in children:
                try:
                    if child.is_symlink() and not self._config.follow_symlinks:
                        continue
                    if child.is_dir():
                        if child.name in ignored or child.name.startswith("."):
                            continue
                        stack.append((child, depth + 1))
                    elif child.is_file():
                        yield child
                except (PermissionError, OSError) as exc:
                    log.debug("path_unreadable", path=str(child), error=str(exc))
                    continue

    def _reader_for(self, path: Path) -> ManifestReader | None:
        for reader in self._readers:
            if reader.claims(path):
                return reader
        return None


def scan_codebase(root: Path) -> CodebaseProfile:
    """Convenience: scan with default readers and config."""
    return CodebaseScanner().scan(root)


_README_LIMIT = 5000


def _read_excerpt(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return text[:_README_LIMIT].strip() or None
