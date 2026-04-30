"""Stack detector — combine manifest reads into stack entries.

Decouples "what was found in manifests" from "how we represent the stack
to the rest of the system". Adding a new ecosystem requires only a new
:class:`ManifestReader` — the detector is reader-agnostic.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import NamedTuple

from tech_scout.codebase.manifest_readers._base import ManifestReadResult
from tech_scout.domain.enums import StackKind
from tech_scout.domain.models import StackEntry


class _Aggregate(NamedTuple):
    name: str
    kind: StackKind
    versions: set[str]
    sources: set[str]
    is_dev_only: bool


class StackDetector:
    """Aggregate manifest results into a list of :class:`StackEntry`."""

    def detect(
        self,
        manifest_results: Iterable[ManifestReadResult],
    ) -> list[StackEntry]:
        results = list(manifest_results)
        entries: list[StackEntry] = []

        # Languages first — one per distinct (language, version) tuple
        lang_seen: dict[tuple[str, str | None], set[str]] = defaultdict(set)
        for r in results:
            key = (r.language, r.language_version)
            lang_seen[key].add(str(r.manifest_path))

        for (language, version), sources in lang_seen.items():
            entries.append(
                StackEntry(
                    kind=StackKind.LANGUAGE,
                    name=language,
                    version=version,
                    source_files=tuple(sorted(sources)),
                    confidence=1.0,
                )
            )

        # Dependencies — group across manifests so we don't duplicate
        aggregates: dict[tuple[str, StackKind], _Aggregate] = {}
        for r in results:
            for dep in r.dependencies:
                if dep.kind == StackKind.OTHER:
                    continue
                key = (dep.name.lower(), dep.kind)
                existing = aggregates.get(key)
                if existing is None:
                    aggregates[key] = _Aggregate(
                        name=dep.name,
                        kind=dep.kind,
                        versions={dep.version} if dep.version else set(),
                        sources={str(r.manifest_path)},
                        is_dev_only=dep.is_dev,
                    )
                else:
                    new_versions = set(existing.versions)
                    if dep.version:
                        new_versions.add(dep.version)
                    new_sources = set(existing.sources) | {str(r.manifest_path)}
                    aggregates[key] = existing._replace(
                        versions=new_versions,
                        sources=new_sources,
                        is_dev_only=existing.is_dev_only and dep.is_dev,
                    )

        for agg in sorted(aggregates.values(), key=lambda a: (a.kind.value, a.name.lower())):
            version = next(iter(sorted(agg.versions))) if len(agg.versions) == 1 else None
            confidence = 1.0 if not agg.is_dev_only else 0.6
            note = "dev/test only" if agg.is_dev_only else None
            entries.append(
                StackEntry(
                    kind=agg.kind,
                    name=agg.name,
                    version=version,
                    source_files=tuple(sorted(agg.sources)),
                    confidence=confidence,
                    notes=note,
                )
            )

        return entries


def detect_stack(manifest_results: Iterable[ManifestReadResult]) -> list[StackEntry]:
    """Convenience function for the default detector."""
    return StackDetector().detect(manifest_results)
