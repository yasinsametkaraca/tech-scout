"""Unit tests for the codebase scanner and stack detector."""

from __future__ import annotations

from pathlib import Path

import pytest

from tech_scout.codebase import scan_codebase
from tech_scout.domain.enums import StackKind
from tech_scout.domain.exceptions import CodebaseScanError


def test_scan_python_fixture(python_fastapi_fixture: Path) -> None:
    profile = scan_codebase(python_fastapi_fixture)
    assert profile.root_path == python_fastapi_fixture
    assert any(e.name == "Python" for e in profile.entries)
    names = {e.name for e in profile.entries}
    assert "fastapi" in names
    assert "langgraph" in names


def test_scan_node_fixture(nextjs_fixture: Path) -> None:
    profile = scan_codebase(nextjs_fixture)
    assert any(e.name == "JavaScript/TypeScript" for e in profile.entries)
    names = {e.name for e in profile.entries}
    assert "next" in names


def test_scan_go_fixture(go_fixture: Path) -> None:
    profile = scan_codebase(go_fixture)
    assert any(e.name == "Go" for e in profile.entries)


def test_scan_empty_codebase(empty_codebase: Path) -> None:
    profile = scan_codebase(empty_codebase)
    assert profile.entries == ()
    assert profile.architecture.integrations_count == 0


def test_scan_nonexistent_raises() -> None:
    with pytest.raises(CodebaseScanError):
        scan_codebase(Path("/definitely/not/a/real/path/zzz"))


def test_scan_skips_node_modules(tmp_path: Path) -> None:
    target = tmp_path / "code"
    target.mkdir()
    (target / "package.json").write_text(
        '{"name":"demo","dependencies":{"next":"14"}}',
        encoding="utf-8",
    )
    # Stuff to ignore
    nm = target / "node_modules" / "fake"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text(
        '{"name":"fake","dependencies":{"deprecated-stuff":"0.0.1"}}',
        encoding="utf-8",
    )

    profile = scan_codebase(target)
    names = {e.name for e in profile.entries}
    assert "next" in names
    assert "deprecated-stuff" not in names


def test_architecture_detects_multi_agent(tmp_path: Path) -> None:
    target = tmp_path / "agentic"
    target.mkdir()
    (target / "pyproject.toml").write_text(
        """\
[project]
name = "demo"
dependencies = ["langgraph>=0.2", "langchain>=0.3"]
""",
        encoding="utf-8",
    )

    profile = scan_codebase(target)
    assert profile.architecture.has_multi_agent
    assert profile.architecture.agent_count is not None and profile.architecture.agent_count >= 1


def test_stack_detector_classifies_kinds(python_fastapi_fixture: Path) -> None:
    profile = scan_codebase(python_fastapi_fixture)
    by_kind: dict[StackKind, list[str]] = {}
    for entry in profile.entries:
        by_kind.setdefault(entry.kind, []).append(entry.name)
    assert "Python" in by_kind.get(StackKind.LANGUAGE, [])
    assert "fastapi" in by_kind.get(StackKind.FRONTEND, [])
    assert "langgraph" in by_kind.get(StackKind.AGENT_FRAMEWORK, [])
