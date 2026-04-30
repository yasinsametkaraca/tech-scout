"""Shared pytest fixtures for tech-scout tests."""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

# Ensure src/ is on sys.path so tests can import tech_scout without install
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Same for scripts/ so integration tests can import _common
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def repo_root() -> Path:
    return _REPO_ROOT


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_codebases_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_codebases"


@pytest.fixture
def python_fastapi_fixture(sample_codebases_dir: Path) -> Path:
    """A minimal Python+FastAPI fixture (created on-the-fly if missing)."""
    target = sample_codebases_dir / "python_fastapi"
    target.mkdir(parents=True, exist_ok=True)
    pyproject = target / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            """\
[project]
name = "demo"
version = "0.1.0"
description = "Test fixture"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110",
    "pydantic>=2.7",
    "langgraph>=0.2",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff"]
""",
            encoding="utf-8",
        )
    readme = target / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Demo\n\nA demo FastAPI app with LangGraph agents.\n",
            encoding="utf-8",
        )
    return target


@pytest.fixture
def nextjs_fixture(sample_codebases_dir: Path) -> Path:
    target = sample_codebases_dir / "nextjs_app"
    target.mkdir(parents=True, exist_ok=True)
    pkg = target / "package.json"
    if not pkg.exists():
        pkg.write_text(
            "{\n"
            '  "name": "demo-next",\n'
            '  "version": "0.1.0",\n'
            '  "type": "module",\n'
            '  "engines": { "node": ">=20" },\n'
            '  "dependencies": {\n'
            '    "next": "14.2.0",\n'
            '    "react": "18.2.0",\n'
            '    "tailwindcss": "3.4.0",\n'
            '    "@anthropic-ai/sdk": "0.30.0"\n'
            "  },\n"
            '  "devDependencies": {\n'
            '    "typescript": "5.4.0",\n'
            '    "vitest": "1.5.0"\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
    return target


@pytest.fixture
def go_fixture(sample_codebases_dir: Path) -> Path:
    target = sample_codebases_dir / "go_service"
    target.mkdir(parents=True, exist_ok=True)
    gomod = target / "go.mod"
    if not gomod.exists():
        gomod.write_text(
            """\
module example.com/demo

go 1.22

require (
\tgithub.com/gin-gonic/gin v1.10.0
\tgo.mongodb.org/mongo-driver v1.15.0
\tgo.opentelemetry.io/otel v1.27.0
)
""",
            encoding="utf-8",
        )
    return target


@pytest.fixture
def empty_codebase(tmp_path: Path) -> Path:
    """A directory with no manifest files."""
    target = tmp_path / "empty"
    target.mkdir()
    return target


@pytest.fixture
def fake_history_root(tmp_path: Path) -> Path:
    """Build a fake research-documentation root with two prior runs."""
    root = tmp_path / "research"
    root.mkdir()

    older = root / "2026-04-15-mcp-protocol-deep-dive"
    older.mkdir()
    (older / "README.md").write_text(
        "# MCP Protocol Deep Dive — Araştırma Paketi\n\nMCP üzerine kapsamlı analiz.\n",
        encoding="utf-8",
    )
    (older / "00-yonetici-ozeti.md").write_text(
        "# MCP Protocol Deep Dive\n\nMCP standardı ajanlar arası iletişim için.\n",
        encoding="utf-8",
    )

    newer = root / "2026-04-22-memory-layer-ai-agents"
    newer.mkdir()
    (newer / "README.md").write_text(
        "# Memory Layer for AI Agents\n",
        encoding="utf-8",
    )
    (newer / "00-yonetici-ozeti.md").write_text(
        "# Memory Layer for AI Agents\n\nMem0 ve benzeri yönetilen hafıza katmanları.\n",
        encoding="utf-8",
    )

    return root


@pytest.fixture
def english_history_root(tmp_path: Path) -> Path:
    """Build a fake research-documentation root with two prior English runs.

    Used to verify the history repository handles English packages — the
    default locale — correctly. The Turkish-only fixture ``fake_history_root``
    covers the other locale.
    """
    root = tmp_path / "research-en"
    root.mkdir()

    older = root / "2026-04-15-mcp-protocol-deep-dive"
    older.mkdir()
    (older / "README.md").write_text(
        "# MCP Protocol Deep Dive — Research Package\n\nIn-depth MCP analysis.\n",
        encoding="utf-8",
    )
    (older / "00-executive-summary.md").write_text(
        "# MCP Protocol Deep Dive\n\nMCP standardizes inter-agent communication.\n",
        encoding="utf-8",
    )

    newer = root / "2026-04-22-memory-layer-ai-agents"
    newer.mkdir()
    (newer / "README.md").write_text(
        "# Memory Layer for AI Agents\n",
        encoding="utf-8",
    )
    (newer / "00-executive-summary.md").write_text(
        "# Memory Layer for AI Agents\n\nMem0 and similar managed memory layers.\n",
        encoding="utf-8",
    )

    return root


@pytest.fixture
def frozen_now() -> datetime:
    return datetime(2026, 4, 29, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def frozen_today() -> date:
    return date(2026, 4, 29)
