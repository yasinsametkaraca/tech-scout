"""High-level architecture inference.

Takes scanner output (manifests + entries + README) and produces a small
:class:`ArchitectureSummary` describing pattern, integrations, and
red-flags. This is heuristic — it's a starting point for the LLM, not
ground truth. Its job is to give Claude a quick orientation.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from tech_scout.codebase.manifest_readers._base import ManifestReadResult
from tech_scout.domain.enums import StackKind
from tech_scout.domain.models import ArchitectureSummary, StackEntry

_AGENT_HINTS = re.compile(
    r"\b(agent|multi[-\s]?agent|langgraph|autogen|crew|swarm|orchestrator)\b",
    re.IGNORECASE,
)
_MONOREPO_HINTS = re.compile(r"\b(monorepo|workspaces?|turborepo|nx)\b", re.IGNORECASE)
_MICROSERVICE_HINTS = re.compile(
    r"\b(micro[-\s]?services?|service\s*mesh|grpc|kubernetes)\b",
    re.IGNORECASE,
)


class ArchitectureSummarizer:
    """Infer :class:`ArchitectureSummary` from scanner output."""

    def summarize(
        self,
        *,
        root: Path,
        entries: Iterable[StackEntry],
        manifest_results: Iterable[ManifestReadResult],
        readme: str | None,
    ) -> ArchitectureSummary:
        entries = tuple(entries)
        manifests = tuple(manifest_results)

        pattern = self._infer_pattern(root=root, manifests=manifests, readme=readme)
        agent_count, has_multi_agent = self._infer_agents(entries=entries, readme=readme)
        integrations_count = sum(
            1
            for e in entries
            if e.kind
            in (
                StackKind.LLM_PROVIDER,
                StackKind.AGENT_FRAMEWORK,
                StackKind.VECTOR_STORE,
                StackKind.DATABASE,
                StackKind.QUEUE,
                StackKind.CLOUD_DEPLOY,
                StackKind.OBSERVABILITY,
                StackKind.INTEGRATION,
            )
        )

        weaknesses = self._weaknesses(entries=entries)
        strengths = self._strengths(entries=entries)
        nxm = self._nxm_problems(entries=entries)
        state_management = self._state_management(entries=entries)

        return ArchitectureSummary(
            pattern=pattern,
            has_multi_agent=has_multi_agent,
            agent_count=agent_count,
            state_management=state_management,
            integrations_count=integrations_count,
            nxm_problems=nxm,
            weaknesses=weaknesses,
            strengths=strengths,
        )

    @staticmethod
    def _infer_pattern(
        *,
        root: Path,
        manifests: tuple[ManifestReadResult, ...],
        readme: str | None,
    ) -> str | None:
        if readme:
            if _MONOREPO_HINTS.search(readme):
                return "monorepo"
            if _MICROSERVICE_HINTS.search(readme):
                return "microservices"
        # Multiple package.json/pyproject in subdirs is a strong monorepo signal
        manifest_dirs = {m.manifest_path.parent for m in manifests}
        if len(manifest_dirs) > 3:
            return "monorepo"
        if (root / "docker-compose.yml").is_file() or (root / "compose.yaml").is_file():
            return "microservices"
        if len(manifests) <= 1:
            return "modular monolith"
        return None

    @staticmethod
    def _infer_agents(
        *, entries: tuple[StackEntry, ...], readme: str | None
    ) -> tuple[int | None, bool]:
        agent_frameworks = [e for e in entries if e.kind == StackKind.AGENT_FRAMEWORK]
        if not agent_frameworks:
            if readme and _AGENT_HINTS.search(readme):
                return None, True
            return None, False
        return len(agent_frameworks), True

    @staticmethod
    def _state_management(entries: tuple[StackEntry, ...]) -> str | None:
        relevant = [
            e
            for e in entries
            if e.kind in (StackKind.DATABASE, StackKind.QUEUE, StackKind.VECTOR_STORE)
        ]
        if not relevant:
            return None
        names = sorted({e.name for e in relevant})
        return ", ".join(names)

    @staticmethod
    def _strengths(entries: tuple[StackEntry, ...]) -> tuple[str, ...]:
        names = {e.name.lower() for e in entries}
        out: list[str] = []
        if {"langgraph", "langchain"} & names:
            out.append("agent framework available (LangGraph/LangChain)")
        if any(e.kind == StackKind.OBSERVABILITY for e in entries):
            out.append("observability stack present")
        if any(e.kind == StackKind.TEST_EVAL for e in entries):
            out.append("testing/eval tooling present")
        return tuple(out)

    @staticmethod
    def _weaknesses(entries: tuple[StackEntry, ...]) -> tuple[str, ...]:
        out: list[str] = []
        if not any(e.kind == StackKind.OBSERVABILITY for e in entries):
            out.append("no observability/logging library detected")
        if not any(e.kind == StackKind.TEST_EVAL for e in entries):
            out.append("no test/eval framework detected")
        return tuple(out)

    @staticmethod
    def _nxm_problems(entries: tuple[StackEntry, ...]) -> tuple[str, ...]:
        integrations = sum(
            1 for e in entries if e.kind in (StackKind.INTEGRATION, StackKind.LLM_PROVIDER)
        )
        if integrations >= 5:
            return ("many tool/LLM integrations — possible N×M maintenance burden",)
        return ()


def summarize_architecture(
    *,
    root: Path,
    entries: Iterable[StackEntry],
    manifest_results: Iterable[ManifestReadResult],
    readme: str | None = None,
) -> ArchitectureSummary:
    """Convenience function for the default summarizer."""
    return ArchitectureSummarizer().summarize(
        root=root,
        entries=entries,
        manifest_results=manifest_results,
        readme=readme,
    )
