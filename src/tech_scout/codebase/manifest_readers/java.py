"""Java/JVM manifest reader: Maven (pom.xml) and Gradle (build.gradle/build.gradle.kts)."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from tech_scout.codebase.manifest_readers._base import (
    ManifestDependency,
    ManifestReader,
    ManifestReadResult,
)
from tech_scout.domain.enums import StackKind
from tech_scout.domain.exceptions import CodebaseScanError

_FILENAMES = {"pom.xml", "build.gradle", "build.gradle.kts"}
_MAVEN_NS = "{http://maven.apache.org/POM/4.0.0}"
_GRADLE_DEP = re.compile(
    r"""(implementation|api|compileOnly|runtimeOnly|testImplementation)\s*[\("\']
        ([\w\.\-]+):([\w\.\-]+):([\w\.\-]+)""",
    re.VERBOSE,
)


class JavaManifestReader(ManifestReader):
    @property
    def ecosystem(self) -> str:
        return "java"

    @property
    def language(self) -> str:
        return "Java/Kotlin (JVM)"

    def claims(self, path: Path) -> bool:
        return path.is_file() and path.name in _FILENAMES

    def read(self, path: Path) -> ManifestReadResult:
        if not path.is_file():
            msg = f"Not a file: {path}"
            raise CodebaseScanError(msg, context={"path": str(path)})

        if path.name == "pom.xml":
            return self._read_pom(path)
        return self._read_gradle(path)

    def _read_pom(self, path: Path) -> ManifestReadResult:
        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError) as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="java",
                language="Java/Kotlin (JVM)",
                raw_metadata={"parse_error": str(exc)},
            )
        root = tree.getroot()
        deps: list[ManifestDependency] = []
        for dep in root.iter(f"{_MAVEN_NS}dependency"):
            group = _xml_text(dep, f"{_MAVEN_NS}groupId")
            artifact = _xml_text(dep, f"{_MAVEN_NS}artifactId")
            version = _xml_text(dep, f"{_MAVEN_NS}version")
            scope = _xml_text(dep, f"{_MAVEN_NS}scope") or ""
            if not group or not artifact:
                continue
            deps.append(
                ManifestDependency(
                    name=f"{group}:{artifact}",
                    version=version,
                    kind=_classify_java(f"{group}:{artifact}"),
                    is_dev=scope.lower() == "test",
                )
            )

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="java",
            language="Java/Kotlin (JVM)",
            dependencies=tuple(deps),
        )

    def _read_gradle(self, path: Path) -> ManifestReadResult:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="java",
                language="Java/Kotlin (JVM)",
                raw_metadata={"parse_error": str(exc)},
            )

        deps: list[ManifestDependency] = []
        for match in _GRADLE_DEP.finditer(text):
            scope, group, artifact, version = match.group(1, 2, 3, 4)
            deps.append(
                ManifestDependency(
                    name=f"{group}:{artifact}",
                    version=version,
                    kind=_classify_java(f"{group}:{artifact}"),
                    is_dev=scope.startswith("test"),
                )
            )

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="java",
            language="Java/Kotlin (JVM)",
            dependencies=tuple(deps),
        )


def _xml_text(element: ET.Element, tag: str) -> str | None:
    found = element.find(tag)
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


_CLASSIFIERS: dict[str, StackKind] = {
    "org.springframework:spring-core": StackKind.FRONTEND,
    "org.springframework.boot:spring-boot-starter-web": StackKind.FRONTEND,
    "io.ktor:ktor-server-core": StackKind.FRONTEND,
    "org.postgresql:postgresql": StackKind.DATABASE,
    "mysql:mysql-connector-java": StackKind.DATABASE,
    "org.mongodb:mongodb-driver-sync": StackKind.DATABASE,
    "redis.clients:jedis": StackKind.QUEUE,
    "io.lettuce:lettuce-core": StackKind.QUEUE,
    "io.opentelemetry:opentelemetry-api": StackKind.OBSERVABILITY,
    "ch.qos.logback:logback-classic": StackKind.OBSERVABILITY,
}


def _classify_java(coordinate: str) -> StackKind:
    return _CLASSIFIERS.get(coordinate, StackKind.OTHER)
