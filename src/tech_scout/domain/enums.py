"""Enumerated types used across the domain.

All enums are :class:`str` subclasses so they serialize cleanly to JSON and
work with Pydantic without converters. Values are language-neutral identifiers;
human-facing text (filenames, labels, prompts) lives in
:mod:`tech_scout.locales`.
"""

from __future__ import annotations

from enum import Enum


class Depth(str, Enum):
    """Research depth — how thorough Phase 4 should be.

    * ``LIGHT`` — fast, surface-level analysis (~15-25 min)
    * ``STANDARD`` — balanced depth, default (~30-45 min)
    * ``DEEP`` — exhaustive analysis (~60-90 min)
    """

    LIGHT = "light"
    STANDARD = "standard"
    DEEP = "deep"


class Language(str, Enum):
    """Output language for the package.

    Use :meth:`from_text` to convert any input form (``"en"``, ``"tr"``,
    ``"english"``, ``"turkish"``, case-insensitive) into a member.
    """

    ENGLISH = "english"
    TURKISH = "turkish"

    @property
    def code(self) -> str:
        """Return the two-letter ISO 639-1 style code (``"en"`` / ``"tr"``)."""
        return _LANGUAGE_CODES[self]

    @classmethod
    def from_text(cls, text: str) -> Language:
        """Resolve a free-form language string into a :class:`Language`.

        Accepts ``"en"``, ``"english"``, ``"tr"``, ``"turkish"`` in any case.
        Raises :class:`ValueError` for unknown input.
        """
        normalized = text.strip().lower()
        for member, code in _LANGUAGE_CODES.items():
            if normalized in {member.value, code}:
                return member
        msg = f"Unknown language: {text!r}. Expected one of: en, tr, english, turkish."
        raise ValueError(msg)


_LANGUAGE_CODES: dict[Language, str] = {
    Language.ENGLISH: "en",
    Language.TURKISH: "tr",
}


class Phase(str, Enum):
    """The seven phases of a research run."""

    PREPARATION = "phase-0-preparation"
    CONTEXT = "phase-1-context"
    DISCOVERY = "phase-2-discovery"
    FILTERING = "phase-3-filtering"
    ANALYSIS = "phase-4-analysis"
    PACKAGING = "phase-5-packaging"
    QUALITY_CHECK = "phase-6-quality-check"


class PhaseStatus(str, Enum):
    """Lifecycle state of a phase within a run."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_USER = "awaiting_user"


class OutputDocSlot(str, Enum):
    """The eight canonical document slots of a research package.

    Slots are language-neutral. The actual output filename and the template
    that renders into it depend on the active :class:`~tech_scout.locales.spec.LocaleSpec`.
    Order matters — it determines the rendering sequence and the README index.
    """

    EXECUTIVE_SUMMARY = "executive_summary"
    DETAILED_ANALYSIS = "detailed_analysis"
    PRESENTATION = "presentation"
    QUICK_REFERENCE = "quick_reference"
    DIAGRAMS = "diagrams"
    SLACK_SUMMARY = "slack_summary"
    SOURCES = "sources"
    README = "readme"

    @classmethod
    def in_order(cls) -> list[OutputDocSlot]:
        """Return all slots in their canonical render order."""
        return [
            cls.EXECUTIVE_SUMMARY,
            cls.DETAILED_ANALYSIS,
            cls.PRESENTATION,
            cls.QUICK_REFERENCE,
            cls.DIAGRAMS,
            cls.SLACK_SUMMARY,
            cls.SOURCES,
            cls.README,
        ]


class SourceCategory(str, Enum):
    """Categories of sources scanned during Phase 2."""

    FOUNDATION_MODELS = "foundation-models"
    AGENT_FRAMEWORKS = "agent-frameworks"
    MEMORY_STATE = "memory-state"
    TOOLS_INTEGRATION = "tools-integration"
    COMPUTE_SANDBOXING = "compute-sandboxing"
    EVALUATION = "evaluation"
    RAG_RETRIEVAL = "rag-retrieval"
    VOICE_MULTIMODAL = "voice-multimodal"
    INFERENCE_SERVING = "inference-serving"
    OPEN_SOURCE_MODELS = "open-source-models"
    RESEARCH_PAPERS = "research-papers"
    PROTOCOLS_STANDARDS = "protocols-standards"
    INFRASTRUCTURE = "infrastructure"
    DEVELOPER_TOOLS = "developer-tools"
    DOMAIN_SPECIFIC = "domain-specific"


class StackKind(str, Enum):
    """Categories used to organize a detected technology stack."""

    LANGUAGE = "language"
    LLM_PROVIDER = "llm-provider"
    AGENT_FRAMEWORK = "agent-framework"
    VECTOR_STORE = "vector-store"
    DATABASE = "database"
    QUEUE = "queue"
    FRONTEND = "frontend"
    CLOUD_DEPLOY = "cloud-deploy"
    OBSERVABILITY = "observability"
    INTEGRATION = "integration"
    TEST_EVAL = "test-eval"
    OTHER = "other"
