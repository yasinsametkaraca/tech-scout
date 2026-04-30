"""Rust manifest reader: Cargo.toml."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from tech_scout.codebase.manifest_readers._base import (
    ManifestDependency,
    ManifestReader,
    ManifestReadResult,
)
from tech_scout.domain.enums import StackKind
from tech_scout.domain.exceptions import CodebaseScanError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef, unused-ignore, import-not-found]


_FILENAMES = {"Cargo.toml"}


class RustManifestReader(ManifestReader):
    @property
    def ecosystem(self) -> str:
        return "rust"

    @property
    def language(self) -> str:
        return "Rust"

    def claims(self, path: Path) -> bool:
        return path.is_file() and path.name in _FILENAMES

    def read(self, path: Path) -> ManifestReadResult:
        if not path.is_file():
            msg = f"Not a file: {path}"
            raise CodebaseScanError(msg, context={"path": str(path)})

        try:
            data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="rust",
                language="Rust",
                raw_metadata={"parse_error": str(exc)},
            )

        deps = _collect_dependencies(data.get("dependencies", {}) or {}, is_dev=False)
        deps.extend(_collect_dependencies(data.get("dev-dependencies", {}) or {}, is_dev=True))

        package = data.get("package", {}) or {}
        meta: dict[str, str] = {}
        if name := package.get("name"):
            meta["project_name"] = str(name)
        if version := package.get("version"):
            meta["project_version"] = str(version)
        if rust_edition := package.get("edition"):
            meta["edition"] = str(rust_edition)

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="rust",
            language="Rust",
            language_version=str(package.get("rust-version"))
            if package.get("rust-version")
            else None,
            dependencies=tuple(deps),
            raw_metadata=meta,
        )


def _collect_dependencies(
    section: dict[str, Any],
    *,
    is_dev: bool,
) -> list[ManifestDependency]:
    out: list[ManifestDependency] = []
    for name, value in section.items():
        if isinstance(value, str):
            version: str | None = value
        elif isinstance(value, dict):
            version = value.get("version") if isinstance(value.get("version"), str) else None
        else:
            version = None
        out.append(
            ManifestDependency(
                name=name,
                version=version,
                kind=_classify_rust(name),
                is_dev=is_dev,
            )
        )
    return out


_CLASSIFIERS: dict[str, StackKind] = {
    "tokio": StackKind.OTHER,
    "axum": StackKind.FRONTEND,
    "actix-web": StackKind.FRONTEND,
    "rocket": StackKind.FRONTEND,
    "hyper": StackKind.FRONTEND,
    "sqlx": StackKind.DATABASE,
    "diesel": StackKind.DATABASE,
    "redis": StackKind.QUEUE,
    "tracing": StackKind.OBSERVABILITY,
    "opentelemetry": StackKind.OBSERVABILITY,
}


def _classify_rust(crate_name: str) -> StackKind:
    return _CLASSIFIERS.get(crate_name, StackKind.OTHER)
