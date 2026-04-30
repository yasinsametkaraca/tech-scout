"""Unit tests for core domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tech_scout.domain.enums import (
    Depth,
    Language,
    OutputDocSlot,
    Phase,
    PhaseStatus,
    SourceCategory,
    StackKind,
)
from tech_scout.domain.models import (
    ArchitectureSummary,
    Candidate,
    CandidateList,
    CandidateScore,
    Finding,
    PhaseProgress,
    ResearchRequest,
    StackEntry,
    UserSelection,
    ValidationIssue,
    ValidationReport,
)
from tech_scout.domain.value_objects import SourceRef


class TestResearchRequest:
    def test_minimum_fields(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        req = ResearchRequest(output_folder=tmp_path)
        assert req.depth == Depth.STANDARD
        assert req.language == Language.ENGLISH
        assert req.slack_language == Language.ENGLISH
        assert not req.has_company_context
        assert not req.has_codebase

    def test_with_company_and_codebase(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        codebase = tmp_path / "code"
        codebase.mkdir()
        req = ResearchRequest(
            output_folder=tmp_path,
            company_name="Acme",
            codebase_path=codebase,
        )
        assert req.has_company_context
        assert req.has_codebase

    def test_nonexistent_codebase_rejected(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValidationError):
            ResearchRequest(
                output_folder=tmp_path,
                codebase_path=tmp_path / "missing",
            )

    def test_turkish_language_accepted(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        req = ResearchRequest(
            output_folder=tmp_path,
            language=Language.TURKISH,
            slack_language=Language.TURKISH,
        )
        assert req.language == Language.TURKISH
        assert req.slack_language == Language.TURKISH

    def test_mixed_languages_accepted(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        req = ResearchRequest(
            output_folder=tmp_path,
            language=Language.ENGLISH,
            slack_language=Language.TURKISH,
        )
        assert req.language == Language.ENGLISH
        assert req.slack_language == Language.TURKISH


class TestLanguageEnum:
    def test_codes(self) -> None:
        assert Language.ENGLISH.code == "en"
        assert Language.TURKISH.code == "tr"

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("en", Language.ENGLISH),
            ("EN", Language.ENGLISH),
            ("english", Language.ENGLISH),
            ("ENGLISH", Language.ENGLISH),
            ("tr", Language.TURKISH),
            ("turkish", Language.TURKISH),
            (" Turkish ", Language.TURKISH),
        ],
    )
    def test_from_text_accepts_codes_and_aliases(self, text: str, expected: Language) -> None:
        assert Language.from_text(text) == expected

    def test_from_text_rejects_unknown(self) -> None:
        with pytest.raises(ValueError):
            Language.from_text("klingon")


class TestCandidateScore:
    def test_valid_overall_accepted(self) -> None:
        score = CandidateScore(impact=9, urgency=7, applicability=6, overall=7.5)
        assert score.overall == 7.5

    def test_inconsistent_overall_rejected(self) -> None:
        with pytest.raises(ValidationError):
            # 0.4*9 + 0.3*7 + 0.3*6 = 3.6 + 2.1 + 1.8 = 7.5, not 9.0
            CandidateScore(impact=9, urgency=7, applicability=6, overall=9.0)

    def test_axis_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CandidateScore(impact=11, urgency=7, applicability=6, overall=8.7)

    def test_axis_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CandidateScore(impact=0, urgency=7, applicability=6, overall=3.9)


class TestCandidate:
    def _make(self, cid: str = "F003") -> Candidate:
        return Candidate(
            id=cid,
            title="AutoHarness paper",
            category=SourceCategory.RESEARCH_PAPERS,
            source=SourceRef(
                url="https://arxiv.org/abs/2603.03329",
                title="AutoHarness paper",
            ),
            score=CandidateScore(impact=9, urgency=7, applicability=6, overall=7.5),
            one_sentence="LLM agents synthesize a code harness instead of acting directly.",
            company_relevance="Fits well with the existing LangGraph state machine.",
            risk_note="Paper still early-stage.",
            suggested_depth=Depth.DEEP,
            estimated_phase_b_minutes=75,
        )

    def test_valid_candidate(self) -> None:
        c = self._make()
        assert c.id == "F003"

    def test_invalid_id_format_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Candidate(
                id="X003",
                title="x",
                category=SourceCategory.RESEARCH_PAPERS,
                source=SourceRef(url="https://example.com", title="t"),
                score=CandidateScore(impact=5, urgency=5, applicability=5, overall=5.0),
                one_sentence="x",
                company_relevance="x",
                risk_note="x",
                estimated_phase_b_minutes=30,
            )

    def test_estimated_minutes_too_low_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Candidate(
                id="F001",
                title="x",
                category=SourceCategory.RESEARCH_PAPERS,
                source=SourceRef(url="https://example.com", title="t"),
                score=CandidateScore(impact=5, urgency=5, applicability=5, overall=5.0),
                one_sentence="x",
                company_relevance="x",
                risk_note="x",
                estimated_phase_b_minutes=5,  # below min of 10
            )


class TestCandidateList:
    def _make_candidate(self, cid: str) -> Candidate:
        return Candidate(
            id=cid,
            title="x",
            category=SourceCategory.RESEARCH_PAPERS,
            source=SourceRef(url="https://example.com", title="t"),
            score=CandidateScore(impact=5, urgency=5, applicability=5, overall=5.0),
            one_sentence="one sentence",
            company_relevance="relevance",
            risk_note="risk",
            estimated_phase_b_minutes=30,
        )

    def test_valid_list(self) -> None:
        cl = CandidateList(
            candidates=(self._make_candidate("F001"), self._make_candidate("F002")),
            scan_summary="sources scanned",
            sources_scanned=10,
            raw_findings_count=20,
        )
        assert len(cl.candidates) == 2

    def test_duplicate_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CandidateList(
                candidates=(self._make_candidate("F001"), self._make_candidate("F001")),
                scan_summary="x",
                sources_scanned=10,
                raw_findings_count=20,
            )

    def test_find_by_id(self) -> None:
        cl = CandidateList(
            candidates=(self._make_candidate("F001"),),
            scan_summary="x",
            sources_scanned=1,
            raw_findings_count=1,
        )
        assert cl.find("F001") is not None
        assert cl.find("F999") is None


class TestStackEntry:
    def test_basic(self) -> None:
        entry = StackEntry(
            kind=StackKind.LANGUAGE,
            name="Python",
            version="3.12",
        )
        assert entry.confidence == 1.0
        assert entry.source_files == ()


class TestArchitectureSummary:
    def test_defaults(self) -> None:
        summary = ArchitectureSummary()
        assert not summary.has_multi_agent
        assert summary.integrations_count == 0


class TestPhaseProgress:
    def test_basic(self) -> None:
        p = PhaseProgress(
            phase=Phase.PREPARATION,
            status=PhaseStatus.NOT_STARTED,
        )
        assert p.error_message is None


class TestUserSelection:
    def test_basic(self) -> None:
        sel = UserSelection(candidate_ids=("F001", "F002"))
        assert sel.depth_override is None

    def test_too_many_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UserSelection(candidate_ids=("F001", "F002", "F003", "F004", "F005", "F006"))

    def test_zero_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UserSelection(candidate_ids=())


class TestValidationReport:
    def test_passed_when_no_errors(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        report = ValidationReport(
            package_path=tmp_path,
            documents_present=("00-executive-summary.md",),
        )
        assert report.passed
        assert report.error_count == 0

    def test_failed_when_documents_missing(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        report = ValidationReport(
            package_path=tmp_path,
            documents_present=(),
            documents_missing=("00-executive-summary.md",),
        )
        assert not report.passed

    def test_warning_does_not_fail(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        report = ValidationReport(
            package_path=tmp_path,
            documents_present=("00-executive-summary.md",),
            issues=(
                ValidationIssue(
                    severity="warning",
                    document="00-executive-summary.md",
                    message="too short",
                ),
            ),
        )
        assert report.passed
        assert report.warning_count == 1


class TestEnumeratedTypes:
    def test_output_doc_in_order_returns_eight(self) -> None:
        order = OutputDocSlot.in_order()
        assert len(order) == 8
        assert order[0] == OutputDocSlot.EXECUTIVE_SUMMARY
        assert order[-1] == OutputDocSlot.README


class TestFinding:
    @pytest.mark.parametrize("fit", ["high", "medium", "low"])
    def test_initial_fit_canonical_english(self, fit: str) -> None:
        Finding(
            id="F001",
            title="x",
            category=SourceCategory.RESEARCH_PAPERS,
            source=SourceRef(url="https://example.com", title="t"),
            summary="summary",
            why_relevant="why",
            initial_fit=fit,
        )

    @pytest.mark.parametrize("fit", ["yüksek", "orta", "düşük", "excellent", ""])
    def test_invalid_fit_rejected(self, fit: str) -> None:
        with pytest.raises(ValidationError):
            Finding(
                id="F001",
                title="x",
                category=SourceCategory.RESEARCH_PAPERS,
                source=SourceRef(url="https://example.com", title="t"),
                summary="summary",
                why_relevant="why",
                initial_fit=fit,
            )

    def test_default_fit_is_medium(self) -> None:
        f = Finding(
            id="F001",
            title="x",
            category=SourceCategory.RESEARCH_PAPERS,
            source=SourceRef(url="https://example.com", title="t"),
            summary="summary",
            why_relevant="why",
        )
        assert f.initial_fit == "medium"
