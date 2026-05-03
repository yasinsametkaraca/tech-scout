"""Python manifest reader: pyproject.toml, requirements.txt, setup.py."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tech_scout.codebase.manifest_readers._base import (
    ManifestDependency,
    ManifestReader,
    ManifestReadResult,
)
from tech_scout.domain.enums import StackKind
from tech_scout.domain.exceptions import CodebaseScanError
from tech_scout.utils.toml_compat import TOMLDecodeError, loads as toml_loads

_FILENAMES = {"pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile"}
_REQ_LINE = re.compile(
    r"^\s*([A-Za-z0-9_.\-]+)\s*(?:\[[^\]]+])?\s*((?:[<>=!~]=?|@)?[^;#\s]*)?",
)


class PythonManifestReader(ManifestReader):
    @property
    def ecosystem(self) -> str:
        return "python"

    @property
    def language(self) -> str:
        return "Python"

    def claims(self, path: Path) -> bool:
        return path.is_file() and path.name in _FILENAMES

    def read(self, path: Path) -> ManifestReadResult:
        if not path.is_file():
            msg = f"Not a file: {path}"
            raise CodebaseScanError(msg, context={"path": str(path)})
        if path.name == "pyproject.toml":
            return self._read_pyproject(path)
        if path.name in {"requirements.txt", "Pipfile"}:
            return self._read_requirements(path)
        if path.name in {"setup.py", "setup.cfg"}:
            return self._read_setup(path)
        msg = f"Unrecognized Python manifest: {path.name}"
        raise CodebaseScanError(msg, context={"path": str(path)})

    def _read_pyproject(self, path: Path) -> ManifestReadResult:
        try:
            data: dict[str, Any] = toml_loads(path.read_text(encoding="utf-8"))
        except (TOMLDecodeError, OSError) as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="python",
                language="Python",
                raw_metadata={"parse_error": str(exc)},
            )

        project = data.get("project", {})
        deps_field = project.get("dependencies", []) or []
        optional = project.get("optional-dependencies", {}) or {}

        deps: list[ManifestDependency] = []
        for raw in deps_field:
            parsed = self._parse_pep508(raw)
            if parsed:
                deps.append(parsed)
        for group_name, items in optional.items():
            for raw in items:
                parsed = self._parse_pep508(raw, is_dev=group_name in {"dev", "test"})
                if parsed:
                    deps.append(parsed)

        language_version = project.get("requires-python") or None

        meta: dict[str, str] = {}
        if name := project.get("name"):
            meta["project_name"] = str(name)
        if version := project.get("version"):
            meta["project_version"] = str(version)

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="python",
            language="Python",
            language_version=language_version,
            dependencies=tuple(deps),
            raw_metadata=meta,
        )

    def _read_requirements(self, path: Path) -> ManifestReadResult:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="python",
                language="Python",
                raw_metadata={"parse_error": str(exc)},
            )

        deps: list[ManifestDependency] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "-")):
                continue
            parsed = self._parse_pep508(stripped)
            if parsed:
                deps.append(parsed)

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="python",
            language="Python",
            dependencies=tuple(deps),
        )

    def _read_setup(self, path: Path) -> ManifestReadResult:
        # We don't execute setup.py. Just record its presence.
        return ManifestReadResult(
            manifest_path=path,
            ecosystem="python",
            language="Python",
            raw_metadata={"note": "setup.py present but not parsed (would require execution)"},
        )

    @staticmethod
    def _parse_pep508(line: str, *, is_dev: bool = False) -> ManifestDependency | None:
        cleaned = line.split(";", maxsplit=1)[0].strip()
        if not cleaned:
            return None
        match = _REQ_LINE.match(cleaned)
        if not match:
            return None
        name = match.group(1)
        version_spec = (match.group(2) or "").strip() or None
        return ManifestDependency(
            name=name.lower(),
            version=version_spec,
            kind=_classify_python(name),
            is_dev=is_dev,
        )


_CLASSIFIERS: dict[str, StackKind] = {
    "openai": StackKind.LLM_PROVIDER,
    "anthropic": StackKind.LLM_PROVIDER,
    "google-generativeai": StackKind.LLM_PROVIDER,
    "google-genai": StackKind.LLM_PROVIDER,
    "boto3": StackKind.CLOUD_DEPLOY,
    "langchain": StackKind.AGENT_FRAMEWORK,
    "langgraph": StackKind.AGENT_FRAMEWORK,
    "llama-index": StackKind.AGENT_FRAMEWORK,
    "autogen": StackKind.AGENT_FRAMEWORK,
    "crewai": StackKind.AGENT_FRAMEWORK,
    "smolagents": StackKind.AGENT_FRAMEWORK,
    "fastapi": StackKind.FRONTEND,
    "uvicorn": StackKind.FRONTEND,
    "starlette": StackKind.FRONTEND,
    "django": StackKind.FRONTEND,
    "flask": StackKind.FRONTEND,
    "pinecone-client": StackKind.VECTOR_STORE,
    "chromadb": StackKind.VECTOR_STORE,
    "weaviate-client": StackKind.VECTOR_STORE,
    "qdrant-client": StackKind.VECTOR_STORE,
    "pymongo": StackKind.DATABASE,
    "psycopg": StackKind.DATABASE,
    "psycopg2": StackKind.DATABASE,
    "psycopg2-binary": StackKind.DATABASE,
    "asyncpg": StackKind.DATABASE,
    "sqlalchemy": StackKind.DATABASE,
    "redis": StackKind.QUEUE,
    "celery": StackKind.QUEUE,
    "kombu": StackKind.QUEUE,
    "pika": StackKind.QUEUE,
    "sentry-sdk": StackKind.OBSERVABILITY,
    "opentelemetry-api": StackKind.OBSERVABILITY,
    "structlog": StackKind.OBSERVABILITY,
    "loguru": StackKind.OBSERVABILITY,
    "prometheus-client": StackKind.OBSERVABILITY,
    "pytest": StackKind.TEST_EVAL,
    "pytest-cov": StackKind.TEST_EVAL,
    "promptfoo": StackKind.TEST_EVAL,
    "langsmith": StackKind.TEST_EVAL,
    "braintrust": StackKind.TEST_EVAL,
}


def _classify_python(package_name: str) -> StackKind:
    return _CLASSIFIERS.get(package_name.lower(), StackKind.OTHER)
