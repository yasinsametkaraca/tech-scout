"""Locale specifications — describe everything language-dependent for one locale.

A :class:`LocaleSpec` is the single source of truth for output filenames,
template subdirectory, validator rules, Stage-A selection prompt, and
display labels in one language. Adding a new locale = registering one
:class:`LocaleSpec` instance in :mod:`tech_scout.locales.registry`.

Notes:

* Field names in templates are language-neutral (e.g. ``topic_title``);
  only prose / labels differ between locales. So a single analyzer JSON
  can render into either language with no field-shape changes.
* Required-section keywords are matched case-insensitively against the
  rendered markdown by :class:`tech_scout.output.validator.PackageValidator`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tech_scout.domain.enums import Language, OutputDocSlot


class LocaleDocumentSpec(BaseModel):
    """Per-locale rendering rules for a single :class:`OutputDocSlot`."""

    model_config = ConfigDict(frozen=True)

    slot: OutputDocSlot
    filename: str = Field(..., min_length=3, max_length=80)
    template_filename: str = Field(..., min_length=3, max_length=80)
    min_words: int = Field(..., ge=10, le=20_000)
    required_section_keywords: tuple[str, ...] = Field(default=())

    @field_validator("filename", "template_filename")
    @classmethod
    def _no_path_separators(cls, v: str) -> str:
        if "/" in v or "\\" in v:
            msg = f"Document filename must not contain path separators: {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("filename")
    @classmethod
    def _filename_is_markdown(cls, v: str) -> str:
        if not v.lower().endswith(".md"):
            msg = f"Output filename must end with .md: {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("template_filename")
    @classmethod
    def _template_is_jinja(cls, v: str) -> str:
        if not v.lower().endswith(".j2"):
            msg = f"Template filename must end with .j2: {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("required_section_keywords")
    @classmethod
    def _keywords_are_lowercase(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for kw in v:
            if kw != kw.lower():
                msg = (
                    f"required_section_keywords must be lowercase for "
                    f"case-insensitive matching: got {kw!r}"
                )
                raise ValueError(msg)
        return v


class LocaleSpec(BaseModel):
    """A complete locale: filenames, templates, prompts, and labels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(..., pattern=r"^[a-z]{2}$")
    display_name: str = Field(..., min_length=1, max_length=80)
    aliases: tuple[str, ...] = Field(default=())
    language: Language
    template_subdir: str = Field(..., pattern=r"^[a-z][a-z0-9_-]*$")
    documents: tuple[LocaleDocumentSpec, ...] = Field(..., min_length=8, max_length=8)
    selection_prompt: str = Field(..., min_length=20, max_length=4000)
    selection_examples: tuple[str, ...] = Field(default=(), max_length=12)
    final_summary_template: str = Field(..., min_length=20, max_length=4000)
    candidate_display_labels: Mapping[str, str] = Field(default_factory=dict)
    score_axis_labels: Mapping[str, str] = Field(default_factory=dict)
    fit_label_map: Mapping[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_documents_cover_all_slots(self) -> LocaleSpec:
        slots_seen = [d.slot for d in self.documents]
        expected = OutputDocSlot.in_order()
        if slots_seen != expected:
            msg = (
                "documents must cover every OutputDocSlot exactly once, in "
                f"canonical order. Got {[s.value for s in slots_seen]}, "
                f"expected {[s.value for s in expected]}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _aliases_lowercase_and_unique(self) -> LocaleSpec:
        seen: set[str] = {self.code}
        for alias in self.aliases:
            if alias != alias.lower():
                msg = f"Aliases must be lowercase: {alias!r}"
                raise ValueError(msg)
            if alias in seen:
                msg = f"Duplicate alias: {alias!r}"
                raise ValueError(msg)
            seen.add(alias)
        return self

    @model_validator(mode="after")
    def _filenames_unique(self) -> LocaleSpec:
        names = [d.filename for d in self.documents]
        if len(set(names)) != len(names):
            msg = f"Output filenames must be unique within a locale: {names}"
            raise ValueError(msg)
        templates = [d.template_filename for d in self.documents]
        if len(set(templates)) != len(templates):
            msg = f"Template filenames must be unique within a locale: {templates}"
            raise ValueError(msg)
        return self

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def document(self, slot: OutputDocSlot) -> LocaleDocumentSpec:
        """Return the :class:`LocaleDocumentSpec` for *slot*."""
        for d in self.documents:
            if d.slot == slot:
                return d
        msg = f"No document spec for slot {slot.value} in locale {self.code}"
        raise KeyError(msg)

    def filename_for(self, slot: OutputDocSlot) -> str:
        """Return the output filename for *slot*."""
        return self.document(slot).filename

    def template_path(self, slot: OutputDocSlot) -> PurePosixPath:
        """Return the template path relative to the templates root.

        Always uses POSIX separators so the same string works on every OS
        when passed to Jinja2's :class:`FileSystemLoader`.
        """
        return PurePosixPath(self.template_subdir) / self.document(slot).template_filename

    def matches(self, code_or_alias: str) -> bool:
        """True if *code_or_alias* (case-insensitive) names this locale."""
        normalized = code_or_alias.strip().lower()
        return normalized == self.code or normalized in self.aliases
