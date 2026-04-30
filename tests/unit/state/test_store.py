"""Unit tests for the run state store."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from tech_scout.domain.enums import (
    Depth,
    Phase,
    PhaseStatus,
    SourceCategory,
)
from tech_scout.domain.exceptions import StateStoreError
from tech_scout.domain.models import (
    Candidate,
    CandidateList,
    CandidateScore,
    PhaseProgress,
    ResearchRequest,
    RunSnapshot,
    UserSelection,
)
from tech_scout.domain.value_objects import RunId, SourceRef
from tech_scout.state import StateStore


def _build_snapshot(tmp_path: Path) -> RunSnapshot:
    request = ResearchRequest(output_folder=tmp_path)
    run_id = RunId(value="2026-04-29-abc123")
    now = datetime(2026, 4, 29, 10, 0, 0)
    phases = tuple(PhaseProgress(phase=p, status=PhaseStatus.NOT_STARTED) for p in Phase)
    return RunSnapshot(
        run_id=run_id,
        request=request,
        phases=phases,
        current_phase=Phase.PREPARATION,
        started_at=now,
        last_updated=now,
    )


def _build_candidate(cid: str = "F001") -> Candidate:
    return Candidate(
        id=cid,
        title="Test",
        category=SourceCategory.RESEARCH_PAPERS,
        source=SourceRef(url="https://arxiv.org/abs/x", title="Test"),
        score=CandidateScore(impact=8, urgency=7, applicability=6, overall=7.1),
        one_sentence="One sentence.",
        company_relevance="Relevance description.",
        risk_note="Risk note here.",
        suggested_depth=Depth.STANDARD,
        estimated_phase_b_minutes=45,
    )


class TestStateStoreInitialization:
    def test_initialize_creates_dir(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        path = store.initialize()
        assert path.is_dir()
        assert path.name == "2026-04-29-abc123"

    def test_state_dir_property(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        assert store.state_dir == tmp_path / ".tech-scout" / "2026-04-29-abc123"

    def test_string_run_id_accepted(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        assert str(store.run_id) == "2026-04-29-abc123"

    def test_invalid_run_id_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(Exception):  # pydantic ValidationError or similar
            StateStore(tmp_path, "not-a-valid-id")


class TestRunSnapshotIO:
    def test_write_and_read_snapshot(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        snapshot = _build_snapshot(tmp_path)
        store.write_run_snapshot(snapshot)
        loaded = store.read_run_snapshot()
        assert loaded is not None
        assert str(loaded.run_id) == str(snapshot.run_id)

    def test_read_missing_returns_none(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        assert store.read_run_snapshot() is None


class TestCandidatesIO:
    def test_write_and_read_candidates(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        cl = CandidateList(
            candidates=(_build_candidate("F001"), _build_candidate("F002")),
            scan_summary="özet",
            sources_scanned=10,
            raw_findings_count=20,
        )
        store.write_candidates(cl)
        loaded = store.read_candidates()
        assert loaded is not None
        assert len(loaded.candidates) == 2
        assert loaded.candidates[0].id == "F001"


class TestSelectionIO:
    def test_write_and_read_selection(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        sel = UserSelection(
            candidate_ids=("F001",),
            depth_override=Depth.DEEP,
        )
        store.write_selection(sel)
        loaded = store.read_selection()
        assert loaded is not None
        assert loaded.candidate_ids == ("F001",)
        assert loaded.depth_override == Depth.DEEP


class TestPhaseProgressIO:
    def test_write_and_read_phase_progress(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        progress = {Phase.PREPARATION.value: PhaseStatus.COMPLETED.value}
        store.write_phase_progress(progress)
        loaded = store.read_phase_progress()
        assert loaded is not None
        assert loaded[Phase.PREPARATION.value] == PhaseStatus.COMPLETED.value


class TestSafetyChecks:
    def test_target_rejects_path_separator(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        with pytest.raises(StateStoreError):
            store._target("../escape.json")  # type: ignore[attr-defined]
        with pytest.raises(StateStoreError):
            store._target("subdir/file.json")  # type: ignore[attr-defined]
        with pytest.raises(StateStoreError):
            store._target("a\\b.json")  # type: ignore[attr-defined]

    def test_target_accepts_simple_filename(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path, "2026-04-29-abc123")
        target = store._target("simple.json")  # type: ignore[attr-defined]
        assert target.name == "simple.json"
        assert target.parent == store.state_dir
