"""Node.js manifest reader: package.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tech_scout.codebase.manifest_readers._base import (
    ManifestDependency,
    ManifestReader,
    ManifestReadResult,
)
from tech_scout.domain.enums import StackKind
from tech_scout.domain.exceptions import CodebaseScanError

_FILENAMES = {"package.json"}


class NodeManifestReader(ManifestReader):
    @property
    def ecosystem(self) -> str:
        return "node"

    @property
    def language(self) -> str:
        return "JavaScript/TypeScript"

    def claims(self, path: Path) -> bool:
        return path.is_file() and path.name in _FILENAMES

    def read(self, path: Path) -> ManifestReadResult:
        if not path.is_file():
            msg = f"Not a file: {path}"
            raise CodebaseScanError(msg, context={"path": str(path)})

        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="node",
                language="JavaScript/TypeScript",
                raw_metadata={"parse_error": str(exc)},
            )

        deps: list[ManifestDependency] = []
        for raw_name, raw_version in (data.get("dependencies") or {}).items():
            deps.append(
                ManifestDependency(
                    name=raw_name,
                    version=str(raw_version),
                    kind=_classify_node(raw_name),
                    is_dev=False,
                )
            )
        for raw_name, raw_version in (data.get("devDependencies") or {}).items():
            deps.append(
                ManifestDependency(
                    name=raw_name,
                    version=str(raw_version),
                    kind=_classify_node(raw_name),
                    is_dev=True,
                )
            )

        engines = data.get("engines") or {}
        node_version = str(engines.get("node")) if engines.get("node") else None

        meta: dict[str, str] = {}
        if name := data.get("name"):
            meta["project_name"] = str(name)
        if version := data.get("version"):
            meta["project_version"] = str(version)
        if "type" in data:
            meta["module_type"] = str(data["type"])
        if data.get("dependencies", {}).get("typescript") or data.get("devDependencies", {}).get(
            "typescript"
        ):
            meta["typescript_present"] = "true"

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="node",
            language="JavaScript/TypeScript",
            language_version=node_version,
            dependencies=tuple(deps),
            raw_metadata=meta,
        )


_CLASSIFIERS: dict[str, StackKind] = {
    "openai": StackKind.LLM_PROVIDER,
    "@anthropic-ai/sdk": StackKind.LLM_PROVIDER,
    "@anthropic-ai/claude-agent-sdk": StackKind.LLM_PROVIDER,
    "@google/generative-ai": StackKind.LLM_PROVIDER,
    "langchain": StackKind.AGENT_FRAMEWORK,
    "@langchain/langgraph": StackKind.AGENT_FRAMEWORK,
    "ai": StackKind.AGENT_FRAMEWORK,
    "next": StackKind.FRONTEND,
    "react": StackKind.FRONTEND,
    "vue": StackKind.FRONTEND,
    "svelte": StackKind.FRONTEND,
    "nuxt": StackKind.FRONTEND,
    "express": StackKind.FRONTEND,
    "fastify": StackKind.FRONTEND,
    "hono": StackKind.FRONTEND,
    "tailwindcss": StackKind.FRONTEND,
    "@radix-ui/react-dialog": StackKind.FRONTEND,
    "pinecone-database": StackKind.VECTOR_STORE,
    "@pinecone-database/pinecone": StackKind.VECTOR_STORE,
    "chromadb": StackKind.VECTOR_STORE,
    "mongodb": StackKind.DATABASE,
    "mongoose": StackKind.DATABASE,
    "pg": StackKind.DATABASE,
    "mysql2": StackKind.DATABASE,
    "drizzle-orm": StackKind.DATABASE,
    "prisma": StackKind.DATABASE,
    "@prisma/client": StackKind.DATABASE,
    "redis": StackKind.QUEUE,
    "ioredis": StackKind.QUEUE,
    "bullmq": StackKind.QUEUE,
    "@sentry/node": StackKind.OBSERVABILITY,
    "@sentry/nextjs": StackKind.OBSERVABILITY,
    "winston": StackKind.OBSERVABILITY,
    "pino": StackKind.OBSERVABILITY,
    "@opentelemetry/api": StackKind.OBSERVABILITY,
    "vitest": StackKind.TEST_EVAL,
    "jest": StackKind.TEST_EVAL,
    "playwright": StackKind.TEST_EVAL,
    "cypress": StackKind.TEST_EVAL,
}


def _classify_node(package_name: str) -> StackKind:
    return _CLASSIFIERS.get(package_name, StackKind.OTHER)
