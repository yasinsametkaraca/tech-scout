"""Integration tests for helper scripts.

These tests invoke each script as a subprocess and parse the JSON envelope.
They use the real filesystem (tmp_path) and real Pydantic validation —
no mocks. They are slower than unit tests; mark as ``integration``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS = _REPO_ROOT / "scripts"


def _run_script(script_name: str, *args: str) -> dict[str, Any]:
    """Run a helper script and return the parsed JSON envelope from stdout."""
    cmd = [sys.executable, str(_SCRIPTS / script_name), *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=str(_REPO_ROOT),
    )
    stdout = (result.stdout or "").strip()
    if not stdout:
        msg = f"Script {script_name} produced no stdout. stderr={result.stderr}"
        raise AssertionError(msg)
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        msg = f"Script {script_name} output is not JSON: {stdout!r} stderr={result.stderr}"
        raise AssertionError(msg) from exc


class TestDoctor:
    def test_runs_and_returns_envelope(self) -> None:
        envelope = _run_script("ts_doctor.py")
        assert envelope["status"] in {"ok", "error"}
        assert "data" in envelope
        if envelope["status"] == "ok":
            data = envelope["data"]
            assert "checks" in data
            assert isinstance(data["checks"], list)
            assert data["python"].startswith("3.")
            # Locale templates checks should appear in the report
            check_names = {c["name"] for c in data["checks"]}
            assert "locale_en_templates" in check_names
            assert "locale_tr_templates" in check_names
        else:
            # When checks fail, the full summary must be preserved in the
            # error envelope's context — otherwise the user can't see
            # which check failed.
            data = envelope["data"]
            assert data["error_type"] == "ConfigurationError"
            assert "context" in data
            assert "checks" in data["context"]
            assert isinstance(data["context"]["checks"], list)


class TestLocaleInfo:
    def test_default_returns_english(self) -> None:
        envelope = _run_script("ts_locale_info.py")
        assert envelope["status"] == "ok"
        assert envelope["data"]["spec"]["code"] == "en"
        assert envelope["data"]["default_code"] == "en"

    def test_explicit_turkish_via_alias(self) -> None:
        envelope = _run_script("ts_locale_info.py", "--code", "turkish")
        assert envelope["status"] == "ok"
        assert envelope["data"]["spec"]["code"] == "tr"

    def test_list_returns_both(self) -> None:
        envelope = _run_script("ts_locale_info.py", "--list")
        assert envelope["status"] == "ok"
        codes = [s["code"] for s in envelope["data"]["locales"]]
        assert codes == ["en", "tr"]

    def test_unknown_locale_errors(self) -> None:
        envelope = _run_script("ts_locale_info.py", "--code", "kk")
        assert envelope["status"] == "error"


class TestScanCodebase:
    def test_scan_python_fixture(self, python_fastapi_fixture: Path) -> None:
        envelope = _run_script("ts_scan_codebase.py", str(python_fastapi_fixture))
        assert envelope["status"] == "ok"
        data = envelope["data"]
        assert data["root_path"] == str(python_fastapi_fixture.resolve())
        assert data["summary"]["entry_count"] >= 1
        assert "Python" in data["summary"]["primary_languages"]

    def test_scan_writes_output_file(self, python_fastapi_fixture: Path, tmp_path: Path) -> None:
        out_file = tmp_path / "profile.json"
        envelope = _run_script(
            "ts_scan_codebase.py",
            str(python_fastapi_fixture),
            "--output",
            str(out_file),
        )
        assert envelope["status"] == "ok"
        assert out_file.is_file()
        loaded = json.loads(out_file.read_text(encoding="utf-8"))
        assert "entries" in loaded

    def test_nonexistent_path_errors(self, tmp_path: Path) -> None:
        envelope = _run_script("ts_scan_codebase.py", str(tmp_path / "missing"))
        assert envelope["status"] == "error"


class TestListHistory:
    def test_empty_root_returns_zero(self, tmp_path: Path) -> None:
        envelope = _run_script("ts_list_history.py", str(tmp_path / "empty"))
        assert envelope["status"] == "ok"
        assert envelope["data"]["total"] == 0
        assert envelope["data"]["entries"] == []

    def test_returns_entries(self, fake_history_root: Path) -> None:
        envelope = _run_script("ts_list_history.py", str(fake_history_root))
        assert envelope["status"] == "ok"
        data = envelope["data"]
        assert data["total"] == 2
        slugs = [e["folder_slug"] for e in data["entries"]]
        assert "memory-layer-ai-agents" in slugs

    def test_limit_parameter(self, fake_history_root: Path) -> None:
        envelope = _run_script("ts_list_history.py", str(fake_history_root), "--limit", "1")
        assert envelope["status"] == "ok"
        assert envelope["data"]["returned"] == 1


class TestSetupRun:
    def test_creates_run_directory_default_english(self, tmp_path: Path) -> None:
        envelope = _run_script(
            "ts_setup_run.py",
            "--output-folder",
            str(tmp_path / "out"),
            "--depth",
            "standard",
        )
        assert envelope["status"] == "ok"
        data = envelope["data"]
        assert data["reused"] is False
        assert data["language"] == "english"
        assert data["locale_code"] == "en"
        state_dir = Path(data["state_dir"])
        assert state_dir.is_dir()
        assert (state_dir / "state.json").is_file()
        assert (state_dir / "audit.jsonl").is_file()

    def test_creates_run_directory_turkish_alias(self, tmp_path: Path) -> None:
        envelope = _run_script(
            "ts_setup_run.py",
            "--output-folder",
            str(tmp_path / "out-tr"),
            "--depth",
            "standard",
            "--language",
            "turkish",
        )
        assert envelope["status"] == "ok"
        assert envelope["data"]["language"] == "turkish"
        assert envelope["data"]["locale_code"] == "tr"

    def test_idempotent_reuse_preserves_locale(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        first = _run_script(
            "ts_setup_run.py",
            "--output-folder",
            str(out),
            "--depth",
            "standard",
            "--language",
            "tr",
        )
        second = _run_script(
            "ts_setup_run.py",
            "--output-folder",
            str(out),
            "--depth",
            "standard",
            "--language",
            "tr",
        )
        assert first["data"]["run_id"] == second["data"]["run_id"]
        assert second["data"]["reused"] is True
        assert second["data"]["locale_code"] == "tr"

    def test_slack_language_overrides_only_slack(self, tmp_path: Path) -> None:
        envelope = _run_script(
            "ts_setup_run.py",
            "--output-folder",
            str(tmp_path / "out-mixed"),
            "--language",
            "en",
            "--slack-language",
            "tr",
        )
        assert envelope["status"] == "ok"
        assert envelope["data"]["locale_code"] == "en"
        assert envelope["data"]["slack_locale_code"] == "tr"


class TestSaveLoadCandidates:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        out_folder = tmp_path / "out"
        setup_envelope = _run_script(
            "ts_setup_run.py",
            "--output-folder",
            str(out_folder),
            "--depth",
            "standard",
        )
        run_id = setup_envelope["data"]["run_id"]

        cand_input = tmp_path / "cand.json"
        cand_input.write_text(
            json.dumps(
                {
                    "candidates": [
                        {
                            "id": "F001",
                            "title": "Test Candidate",
                            "category": "research-papers",
                            "source": {
                                "url": "https://arxiv.org/abs/x",
                                "title": "Test",
                            },
                            "score": {
                                "impact": 8,
                                "urgency": 7,
                                "applicability": 6,
                                "overall": 7.1,
                            },
                            "one_sentence": "Test sentence.",
                            "company_relevance": "Relevance description.",
                            "risk_note": "Risk note.",
                            "suggested_depth": "standard",
                            "estimated_phase_b_minutes": 45,
                        }
                    ],
                    "scan_summary": "Test scan summary.",
                    "sources_scanned": 5,
                    "raw_findings_count": 10,
                }
            ),
            encoding="utf-8",
        )

        save_envelope = _run_script(
            "ts_save_candidates.py",
            "--run-id",
            run_id,
            "--output-folder",
            str(out_folder),
            "--candidates-file",
            str(cand_input),
        )
        assert save_envelope["status"] == "ok"
        assert save_envelope["data"]["candidate_count"] == 1

        load_envelope = _run_script(
            "ts_load_candidates.py",
            "--run-id",
            run_id,
            "--output-folder",
            str(out_folder),
        )
        assert load_envelope["status"] == "ok"
        assert load_envelope["data"]["candidate_ids"] == ["F001"]


def _english_executive_summary_context() -> dict[str, Any]:
    return {
        "topic_title": "Test Topic",
        "generated_date": "2026-04-29",
        "author": "Test Author",
        "company_name": "Acme",
        "headline_message": "One sentence pitch.",
        "problem_description": "Problem statement.",
        "solution_description": "Solution outline.",
        "investment": {"summary": "$50K / 4 weeks", "engineer_weeks": "4"},
        "roi": {"payback_period": "6 months", "annual_value": "$200K"},
        "risk_level": "Low",
        "plan_phases": [
            {"timeframe": "0-4 weeks", "description": "Phase 1"},
            {"timeframe": "1-3 months", "description": "Phase 2"},
            {"timeframe": "3-6 months", "description": "Phase 3"},
        ],
        "decisions_needed": ["A?", "B?", "C?"],
        "call_to_action": "Do this.",
    }


class TestRenderDoc:
    def test_renders_executive_summary_english(self, tmp_path: Path) -> None:
        ctx_file = tmp_path / "ctx.json"
        ctx_file.write_text(json.dumps(_english_executive_summary_context()), encoding="utf-8")
        out_folder = tmp_path / "package"
        envelope = _run_script(
            "ts_render_doc.py",
            "--slot",
            "executive_summary",
            "--context-file",
            str(ctx_file),
            "--output-folder",
            str(out_folder),
            "--locale-code",
            "en",
        )
        assert envelope["status"] == "ok"
        assert envelope["data"]["filename"] == "00-executive-summary.md"
        rendered = (out_folder / "00-executive-summary.md").read_text(encoding="utf-8")
        assert "Test Topic" in rendered
        assert "Do this." in rendered

    def test_renders_executive_summary_turkish(self, tmp_path: Path) -> None:
        # Turkish run: same field names, Turkish prose
        ctx = _english_executive_summary_context()
        ctx["headline_message"] = "Tek cümlelik özet."
        ctx["problem_description"] = "Problem var."
        ctx["solution_description"] = "Çözüm bu."
        ctx["risk_level"] = "Düşük"
        ctx["call_to_action"] = "Bunu yap."
        ctx_file = tmp_path / "ctx.json"
        ctx_file.write_text(json.dumps(ctx), encoding="utf-8")
        out_folder = tmp_path / "package-tr"
        envelope = _run_script(
            "ts_render_doc.py",
            "--slot",
            "executive_summary",
            "--context-file",
            str(ctx_file),
            "--output-folder",
            str(out_folder),
            "--locale-code",
            "tr",
        )
        assert envelope["status"] == "ok"
        assert envelope["data"]["filename"] == "00-yonetici-ozeti.md"
        rendered = (out_folder / "00-yonetici-ozeti.md").read_text(encoding="utf-8")
        assert "Bunu yap." in rendered

    def test_missing_field_errors(self, tmp_path: Path) -> None:
        # Missing required fields — strict undefined should fail
        ctx_file = tmp_path / "ctx.json"
        ctx_file.write_text(json.dumps({"topic_title": "x"}), encoding="utf-8")
        envelope = _run_script(
            "ts_render_doc.py",
            "--slot",
            "executive_summary",
            "--context-file",
            str(ctx_file),
            "--output-folder",
            str(tmp_path / "out"),
        )
        assert envelope["status"] == "error"


def _write_minimal_english_package(target: Path) -> None:
    """Build a structurally valid English package for validator integration test."""
    target.mkdir(parents=True, exist_ok=True)
    (target / "00-executive-summary.md").write_text(
        "# Executive Summary\n\n## Headline Message\n\nMessage.\n\n"
        "## Problem\n\nProblem.\n\n## Solution\n\nSolution.\n\n"
        "## Investment\n\nLow.\n\n## Call to Action\n\nAct.\n\n" + "x " * 250,
        encoding="utf-8",
    )
    (target / "01-detailed-analysis.md").write_text(
        "# Detailed Analysis\n\n## Executive Summary\n\nSummary.\n\n"
        "## Gap Analysis\n\nGap.\n\n## Implementation\n\nLayers.\n\n"
        "## Cost\n\nCost.\n\n## Risk\n\nRisk.\n\n## Roadmap\n\nRoadmap.\n\n"
        "## Conclusion\n\nConclusion.\n\n" + "word " * 1500,
        encoding="utf-8",
    )
    (target / "02-presentation.md").write_text(
        "# Presentation\n\n## SLIDE 1: Cover\n\n" + "speech " * 800,
        encoding="utf-8",
    )
    (target / "03-quick-reference.md").write_text(
        "# Quick Reference\n\n## Core Concepts\n\nConcepts.\n\n"
        "## Three Core Messages\n\nMessages.\n\n## Closing\n\nEnd.\n\n" + "x " * 250,
        encoding="utf-8",
    )
    (target / "04-diagrams.md").write_text(
        "# Diagrams\n\n```mermaid\ngraph TD\n  A --> B\n```\n" + "x " * 100,
        encoding="utf-8",
    )
    (target / "05-slack-summary.md").write_text(
        "# Slack\n\nMessage.\n" + "x " * 100,
        encoding="utf-8",
    )
    (target / "06-sources.md").write_text(
        "# Sources\n\n[link](https://example.com)\n" + "x " * 100,
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        "# README\n\nPackage.\n" + "x " * 80,
        encoding="utf-8",
    )


class TestValidatePackage:
    def test_complete_english_package(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        _write_minimal_english_package(pkg)
        envelope = _run_script(
            "ts_validate_package.py",
            "--output-folder",
            str(pkg),
            "--locale-code",
            "en",
        )
        assert envelope["status"] == "ok"
        assert envelope["data"]["passed"] is True
        assert envelope["data"]["locale_code"] == "en"

    def test_english_package_validated_against_turkish_locale_fails(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg-en"
        _write_minimal_english_package(pkg)
        envelope = _run_script(
            "ts_validate_package.py",
            "--output-folder",
            str(pkg),
            "--locale-code",
            "tr",
        )
        # Turkish locale expects Turkish filenames; English ones are missing
        assert envelope["status"] == "error"
        assert "documents_missing" in envelope["data"]["context"]

    def test_missing_documents_fail(self, tmp_path: Path) -> None:
        # Empty package
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        envelope = _run_script(
            "ts_validate_package.py",
            "--output-folder",
            str(pkg),
            "--locale-code",
            "en",
        )
        assert envelope["status"] == "error"
        assert "documents_missing" in envelope["data"]["context"]
