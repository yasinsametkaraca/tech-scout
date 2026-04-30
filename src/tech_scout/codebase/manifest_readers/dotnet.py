""".NET manifest reader: .csproj, .fsproj."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from tech_scout.codebase.manifest_readers._base import (
    ManifestDependency,
    ManifestReader,
    ManifestReadResult,
)
from tech_scout.domain.enums import StackKind
from tech_scout.domain.exceptions import CodebaseScanError

_EXTENSIONS = {".csproj", ".fsproj", ".vbproj"}


class DotNetManifestReader(ManifestReader):
    @property
    def ecosystem(self) -> str:
        return "dotnet"

    @property
    def language(self) -> str:
        return "C#/F#/.NET"

    def claims(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in _EXTENSIONS

    def read(self, path: Path) -> ManifestReadResult:
        if not path.is_file():
            msg = f"Not a file: {path}"
            raise CodebaseScanError(msg, context={"path": str(path)})

        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError) as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="dotnet",
                language="C#/F#/.NET",
                raw_metadata={"parse_error": str(exc)},
            )

        root = tree.getroot()
        deps: list[ManifestDependency] = []
        target_framework: str | None = None

        for prop in root.iter("TargetFramework"):
            if prop.text:
                target_framework = prop.text.strip()
                break

        for pkg in root.iter("PackageReference"):
            name = pkg.get("Include")
            version = pkg.get("Version")
            if not name:
                continue
            deps.append(
                ManifestDependency(
                    name=name,
                    version=version,
                    kind=_classify_dotnet(name),
                )
            )

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="dotnet",
            language="C#/F#/.NET",
            language_version=target_framework,
            dependencies=tuple(deps),
        )


_CLASSIFIERS: dict[str, StackKind] = {
    "Microsoft.AspNetCore.App": StackKind.FRONTEND,
    "Microsoft.AspNetCore.Mvc": StackKind.FRONTEND,
    "Microsoft.EntityFrameworkCore": StackKind.DATABASE,
    "Npgsql.EntityFrameworkCore.PostgreSQL": StackKind.DATABASE,
    "MongoDB.Driver": StackKind.DATABASE,
    "StackExchange.Redis": StackKind.QUEUE,
    "Sentry": StackKind.OBSERVABILITY,
    "Serilog": StackKind.OBSERVABILITY,
    "OpenTelemetry": StackKind.OBSERVABILITY,
    "Azure.AI.OpenAI": StackKind.LLM_PROVIDER,
}


def _classify_dotnet(package_name: str) -> StackKind:
    return _CLASSIFIERS.get(package_name, StackKind.OTHER)
