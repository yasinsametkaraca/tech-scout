"""Pydantic data models for the tech-scout domain.

These models are the lingua franca crossing module boundaries. They are
serialized to JSON for state files and CLI envelopes, and they validate
structural invariants on construction.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tech_scout.domain.enums import (
    Depth,
    Language,
    Phase,
    PhaseStatus,
    SourceCategory,
    StackKind,
)
from tech_scout.domain.value_objects import RunId, SourceRef, TimeWindow

# ---------------------------------------------------------------------------
# Research request (Phase 0 input)
# ---------------------------------------------------------------------------


class ResearchRequest(BaseModel):
    """User-supplied parameters for a research run.

    Only ``output_folder`` is strictly required; everything else is optional
    and drives different branches of the workflow (e.g. codebase-aware vs.
    website-only vs. generic mode).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    company_name: str | None = Field(default=None, max_length=200)
    company_description: str | None = Field(default=None, max_length=2000)
    company_website: str | None = Field(default=None, max_length=500)
    codebase_path: Path | None = None
    focus_area: str | None = Field(default=None, max_length=500)
    time_window: TimeWindow | None = None
    output_folder: Path
    language: Language = Language.ENGLISH
    slack_language: Language = Language.ENGLISH
    depth: Depth = Depth.STANDARD
    prior_research_root: Path | None = None
    initiated_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def _validate_consistency(self) -> ResearchRequest:
        if self.codebase_path is not None and not self.codebase_path.exists():
            msg = f"codebase_path does not exist: {self.codebase_path}"
            raise ValueError(msg)
        if (
            self.prior_research_root is not None
            and self.prior_research_root.exists()
            and not self.prior_research_root.is_dir()
        ):
            msg = f"prior_research_root must be a directory: {self.prior_research_root}"
            raise ValueError(msg)
        return self

    @property
    def has_company_context(self) -> bool:
        return self.company_name is not None or self.company_description is not None

    @property
    def has_codebase(self) -> bool:
        return self.codebase_path is not None


# ---------------------------------------------------------------------------
# Codebase profile (Phase 1 output)
# ---------------------------------------------------------------------------


class StackEntry(BaseModel):
    """A single technology detected in the codebase."""

    model_config = ConfigDict(frozen=True)

    kind: StackKind
    name: str = Field(..., min_length=1, max_length=100)
    version: str | None = Field(default=None, max_length=50)
    source_files: tuple[str, ...] = Field(default=())
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str | None = Field(default=None, max_length=500)


class ArchitectureSummary(BaseModel):
    """High-level architectural facts inferred from the codebase."""

    pattern: str | None = Field(default=None, max_length=200)
    has_multi_agent: bool = False
    agent_count: int | None = Field(default=None, ge=0)
    state_management: str | None = Field(default=None, max_length=300)
    integrations_count: int = Field(default=0, ge=0)
    nxm_problems: tuple[str, ...] = Field(default=())
    weaknesses: tuple[str, ...] = Field(default=())
    strengths: tuple[str, ...] = Field(default=())


class CodebaseProfile(BaseModel):
    """Result of scanning a codebase."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=1, ge=1)
    root_path: Path
    scanned_at: datetime = Field(default_factory=datetime.now)
    entries: tuple[StackEntry, ...]
    architecture: ArchitectureSummary
    readme_excerpt: str | None = Field(default=None, max_length=5000)
    manifest_files_found: tuple[str, ...] = Field(default=())

    def by_kind(self, kind: StackKind) -> tuple[StackEntry, ...]:
        return tuple(e for e in self.entries if e.kind == kind)

    def primary_languages(self) -> tuple[StackEntry, ...]:
        return self.by_kind(StackKind.LANGUAGE)


# ---------------------------------------------------------------------------
# History entries (Phase 0 input)
# ---------------------------------------------------------------------------


class HistoryEntry(BaseModel):
    """One past research run, summarized for deduplication."""

    model_config = ConfigDict(frozen=True)

    run_id: RunId | None = None
    folder_path: Path
    folder_slug: str = Field(..., min_length=1)
    title: str | None = Field(default=None, max_length=300)
    primary_topic: str | None = Field(default=None, max_length=500)
    categories: tuple[SourceCategory, ...] = Field(default=())
    completed_date: date | None = None
    summary: str | None = Field(default=None, max_length=3000)


class PriorRun(BaseModel):
    """Detailed view of a prior run (used by /tech-scout-show)."""

    model_config = ConfigDict(frozen=True)

    entry: HistoryEntry
    package_files: tuple[Path, ...]
    selected_candidate_ids: tuple[str, ...] = Field(default=())


# ---------------------------------------------------------------------------
# Findings & candidates (Phase 2-3)
# ---------------------------------------------------------------------------


class CandidateScore(BaseModel):
    """Three-axis scoring for a candidate finding.

    Each axis is 1-10. ``overall`` is computed as
    ``0.4 * impact + 0.3 * urgency + 0.3 * applicability``.
    """

    model_config = ConfigDict(frozen=True)

    impact: int = Field(..., ge=1, le=10)
    urgency: int = Field(..., ge=1, le=10)
    applicability: int = Field(..., ge=1, le=10)
    overall: float = Field(..., ge=1.0, le=10.0)

    @model_validator(mode="after")
    def _check_overall(self) -> CandidateScore:
        expected = 0.4 * self.impact + 0.3 * self.urgency + 0.3 * self.applicability
        if abs(self.overall - expected) > 0.05:
            msg = (
                "overall does not match weighted sum of axes: "
                f"expected {expected:.2f}, got {self.overall:.2f}"
            )
            raise ValueError(msg)
        return self


class Finding(BaseModel):
    """A raw finding emitted by Phase 2 (discovery), pre-scoring."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., pattern=r"^F\d{3}$")
    title: str = Field(..., min_length=1, max_length=300)
    category: SourceCategory
    source: SourceRef
    summary: str = Field(..., min_length=1, max_length=1000)
    why_relevant: str = Field(..., min_length=1, max_length=500)
    initial_fit: str = Field(default="medium", pattern=r"^(high|medium|low)$")


class Candidate(BaseModel):
    """A scored, presentation-ready candidate (Phase 3 output).

    These are the cards shown to the user at the end of Stage A. The user
    picks 1+ of these for deep analysis in Stage B.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., pattern=r"^F\d{3}$")
    title: str = Field(..., min_length=1, max_length=300)
    category: SourceCategory
    source: SourceRef
    score: CandidateScore
    one_sentence: str = Field(..., min_length=1, max_length=400)
    company_relevance: str = Field(..., min_length=1, max_length=2000)
    risk_note: str = Field(..., min_length=1, max_length=500)
    overlaps_with_prior: str | None = Field(default=None, max_length=300)
    suggested_depth: Depth = Depth.STANDARD
    estimated_phase_b_minutes: int = Field(..., ge=10, le=240)


class CandidateList(BaseModel):
    """Full Phase 3 output: the shortlist + honourable mentions."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=1, ge=1)
    candidates: tuple[Candidate, ...] = Field(..., min_length=1, max_length=20)
    honourable_mentions: tuple[Finding, ...] = Field(default=(), max_length=10)
    scan_summary: str = Field(..., min_length=1, max_length=3000)
    sources_scanned: int = Field(..., ge=0)
    raw_findings_count: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _ids_unique(self) -> CandidateList:
        ids = [c.id for c in self.candidates]
        if len(ids) != len(set(ids)):
            msg = "Candidate IDs must be unique within a CandidateList"
            raise ValueError(msg)
        return self

    def find(self, candidate_id: str) -> Candidate | None:
        return next((c for c in self.candidates if c.id == candidate_id), None)


# ---------------------------------------------------------------------------
# User selection (between Stage A and Stage B)
# ---------------------------------------------------------------------------


class UserSelection(BaseModel):
    """The user's pick at the end of Stage A."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=1, ge=1)
    candidate_ids: tuple[str, ...] = Field(..., min_length=1, max_length=5)
    depth_override: Depth | None = None
    notes: str | None = Field(default=None, max_length=1000)
    decided_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Run progress
# ---------------------------------------------------------------------------


class PhaseProgress(BaseModel):
    """Status of a single phase within a run."""

    model_config = ConfigDict(frozen=True)

    phase: Phase
    status: PhaseStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = Field(default=None, max_length=2000)


class RunSnapshot(BaseModel):
    """Top-level run state used for resume."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=1, ge=1)
    run_id: RunId
    request: ResearchRequest
    phases: tuple[PhaseProgress, ...] = Field(..., min_length=1)
    current_phase: Phase
    started_at: datetime
    last_updated: datetime

    def find_phase(self, phase: Phase) -> PhaseProgress | None:
        return next((p for p in self.phases if p.phase == phase), None)


# ---------------------------------------------------------------------------
# Package validation result (Phase 6)
# ---------------------------------------------------------------------------


class ValidationIssue(BaseModel):
    """A single problem found during Phase 6 quality check."""

    model_config = ConfigDict(frozen=True)

    severity: Annotated[str, Field(pattern=r"^(error|warning|info)$")]
    document: str
    section: str | None = None
    message: str = Field(..., min_length=1, max_length=1000)


class ValidationReport(BaseModel):
    """Aggregate result of Phase 6."""

    model_config = ConfigDict(frozen=True)

    package_path: Path
    issues: tuple[ValidationIssue, ...] = Field(default=())
    documents_present: tuple[str, ...]
    documents_missing: tuple[str, ...] = Field(default=())

    @property
    def passed(self) -> bool:
        return not any(i.severity == "error" for i in self.issues) and not self.documents_missing

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")
