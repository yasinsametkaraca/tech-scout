"""Go manifest reader: go.mod."""

from __future__ import annotations

import re
from pathlib import Path

from tech_scout.codebase.manifest_readers._base import (
    ManifestDependency,
    ManifestReader,
    ManifestReadResult,
)
from tech_scout.domain.enums import StackKind
from tech_scout.domain.exceptions import CodebaseScanError

_FILENAMES = {"go.mod"}
_GO_VERSION = re.compile(r"^go\s+(\S+)\s*$", re.MULTILINE)
_REQUIRE_BLOCK = re.compile(r"require\s*\((.*?)\)", re.DOTALL)
_REQUIRE_LINE = re.compile(r"^\s*([\w\.\-/]+)\s+(\S+)(?:\s+//\s*(.*))?$", re.MULTILINE)
_INDIRECT_HINT = "indirect"


class GoManifestReader(ManifestReader):
    @property
    def ecosystem(self) -> str:
        return "go"

    @property
    def language(self) -> str:
        return "Go"

    def claims(self, path: Path) -> bool:
        return path.is_file() and path.name in _FILENAMES

    def read(self, path: Path) -> ManifestReadResult:
        if not path.is_file():
            msg = f"Not a file: {path}"
            raise CodebaseScanError(msg, context={"path": str(path)})

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="go",
                language="Go",
                raw_metadata={"parse_error": str(exc)},
            )

        version_match = _GO_VERSION.search(text)
        language_version = version_match.group(1) if version_match else None

        deps: list[ManifestDependency] = []
        for block_match in _REQUIRE_BLOCK.finditer(text):
            block = block_match.group(1)
            for dep_match in _REQUIRE_LINE.finditer(block):
                name = dep_match.group(1)
                version = dep_match.group(2)
                comment = (dep_match.group(3) or "").lower()
                deps.append(
                    ManifestDependency(
                        name=name,
                        version=version,
                        kind=_classify_go(name),
                        is_dev=_INDIRECT_HINT in comment,
                    )
                )

        # single-line require directives outside blocks
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("require ") and "(" not in stripped:
                parts = stripped.split()
                if len(parts) >= 3:
                    name = parts[1]
                    version = parts[2]
                    deps.append(
                        ManifestDependency(
                            name=name,
                            version=version,
                            kind=_classify_go(name),
                        )
                    )

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="go",
            language="Go",
            language_version=language_version,
            dependencies=tuple(deps),
        )


_CLASSIFIERS: dict[str, StackKind] = {
    "github.com/gin-gonic/gin": StackKind.FRONTEND,
    "github.com/labstack/echo": StackKind.FRONTEND,
    "github.com/gofiber/fiber": StackKind.FRONTEND,
    "github.com/go-chi/chi": StackKind.FRONTEND,
    "go.mongodb.org/mongo-driver": StackKind.DATABASE,
    "github.com/jackc/pgx": StackKind.DATABASE,
    "github.com/lib/pq": StackKind.DATABASE,
    "github.com/redis/go-redis": StackKind.QUEUE,
    "github.com/aws/aws-sdk-go-v2": StackKind.CLOUD_DEPLOY,
    "github.com/aws/aws-sdk-go": StackKind.CLOUD_DEPLOY,
    "github.com/getsentry/sentry-go": StackKind.OBSERVABILITY,
    "go.opentelemetry.io/otel": StackKind.OBSERVABILITY,
    "github.com/sirupsen/logrus": StackKind.OBSERVABILITY,
    "go.uber.org/zap": StackKind.OBSERVABILITY,
}


def _classify_go(import_path: str) -> StackKind:
    for prefix, kind in _CLASSIFIERS.items():
        if import_path.startswith(prefix):
            return kind
    return StackKind.OTHER
