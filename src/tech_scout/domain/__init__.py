"""Domain layer — pure data structures and rules, no I/O.

The domain layer is the innermost ring of the architecture. Modules here
must not import from any other internal module (config, codebase, output,
etc.) and must not perform I/O. They define the vocabulary used by the
rest of the codebase.

Key types:

* :class:`~tech_scout.domain.models.ResearchRequest` — input parameters for a run
* :class:`~tech_scout.domain.models.Candidate` — a single Phase 3 finding card
* :class:`~tech_scout.domain.models.CandidateScore` — Impact/Urgency/Applicability scores
* :class:`~tech_scout.domain.value_objects.RunId` — identifier for a research run
* :class:`~tech_scout.domain.enums.Depth` — research depth (light/standard/deep)
* :class:`~tech_scout.domain.enums.Language` — output language (English / Turkish, …)
* :class:`~tech_scout.domain.enums.OutputDocSlot` — language-neutral document slot
"""

from __future__ import annotations

from tech_scout.domain.enums import (
    Depth,
    Language,
    OutputDocSlot,
    Phase,
    PhaseStatus,
    SourceCategory,
)
from tech_scout.domain.exceptions import (
    CodebaseScanError,
    ConfigurationError,
    HistoryLookupError,
    LocaleNotFoundError,
    StateStoreError,
    TechScoutError,
    TemplateRenderError,
    ValidationError,
)
from tech_scout.domain.models import (
    Candidate,
    CandidateScore,
    CodebaseProfile,
    HistoryEntry,
    PriorRun,
    ResearchRequest,
    StackEntry,
)
from tech_scout.domain.value_objects import (
    OutputPath,
    RunId,
    SourceRef,
    TimeWindow,
)

__all__ = [
    # Enums
    "Depth",
    "Language",
    "OutputDocSlot",
    "Phase",
    "PhaseStatus",
    "SourceCategory",
    # Exceptions
    "CodebaseScanError",
    "ConfigurationError",
    "HistoryLookupError",
    "LocaleNotFoundError",
    "StateStoreError",
    "TechScoutError",
    "TemplateRenderError",
    "ValidationError",
    # Models
    "Candidate",
    "CandidateScore",
    "CodebaseProfile",
    "HistoryEntry",
    "PriorRun",
    "ResearchRequest",
    "StackEntry",
    # Value objects
    "OutputPath",
    "RunId",
    "SourceRef",
    "TimeWindow",
]
